//! Opt-in finite f32 linear using the existing pure-Rust GEMM and bias destination.
//! Forward/graph acceptance does not certify the compiled backward implementation.
use crate::{Error, Result};
use burn::backend::{
    Autodiff, Backend, DType, Dispatch, Flex, TensorMetadata,
    autodiff::{
        checkpoint::{base::Checkpointer, strategy::CheckpointStrategy},
        grads::Gradients,
        ops::{Backward, Ops, OpsKind},
    },
    backend_extension,
    ops::FloatTensorOps,
    tensor::FloatTensor,
};
use burn::tensor::Tensor;

#[backend_extension(Flex, Autodiff)]
trait FusedLinearOps: Backend {
    fn finite_fused_linear(
        x: FloatTensor<Self>,
        weight: FloatTensor<Self>,
        bias: FloatTensor<Self>,
    ) -> FloatTensor<Self>;
}

/// Prove the entire nonnegative-strided logical view lies in its typed storage.
fn checked_view(t: &FloatTensor<Flex>, dims: &[usize]) -> (usize, Vec<usize>) {
    assert_eq!(t.dtype(), DType::F32);
    let layout = t.layout();
    assert_eq!(layout.shape().num_dims(), dims.len());
    assert_eq!(layout.strides().len(), dims.len());
    let start = layout.start_offset();
    let mut last = start;
    let mut strides = Vec::with_capacity(dims.len());
    for (i, &n) in dims.iter().enumerate() {
        assert!(n > 0 && layout.shape()[i] == n);
        let stride = usize::try_from(layout.strides()[i]).expect("negative strides unsupported");
        assert!(stride <= isize::MAX as usize / size_of::<f32>());
        last = last
            .checked_add((n - 1).checked_mul(stride).expect("stride overflow"))
            .expect("view offset overflow");
        strides.push(stride);
    }
    let bytes = last
        .checked_add(1)
        .and_then(|n| n.checked_mul(size_of::<f32>()))
        .expect("view byte range overflow");
    assert!(bytes <= isize::MAX as usize);
    assert!(last < t.storage::<f32>().len(), "view exceeds storage");
    (start, strides)
}

impl FusedLinearOps for Flex {
    fn finite_fused_linear(
        x: FloatTensor<Self>,
        weight: FloatTensor<Self>,
        bias: FloatTensor<Self>,
    ) -> FloatTensor<Self> {
        assert_eq!(x.shape().num_dims(), 2);
        assert_eq!(weight.shape().num_dims(), 2);
        assert_eq!(bias.shape().num_dims(), 1);
        let (m, k, n) = (x.shape()[0], x.shape()[1], weight.shape()[1]);
        assert!((1..=120).contains(&m) && (1..=128).contains(&k) && (1..=128).contains(&n));
        assert_eq!(weight.shape()[0], k);
        assert_eq!(bias.shape()[0], n);
        let (xo, xs) = checked_view(&x, &[m, k]);
        let (wo, ws) = checked_view(&weight, &[k, n]);
        let (bo, bs) = checked_view(&bias, &[n]);
        let xv = x.storage::<f32>();
        let wv = weight.storage::<f32>();
        let bv = bias.storage::<f32>();
        for i in 0..m {
            for t in 0..k {
                assert!(
                    xv[xo + i * xs[0] + t * xs[1]].is_finite(),
                    "nonfinite input"
                );
            }
        }
        for t in 0..k {
            for j in 0..n {
                assert!(
                    wv[wo + t * ws[0] + j * ws[1]].is_finite(),
                    "nonfinite weight"
                );
            }
        }
        let count = m.checked_mul(n).expect("output size overflow");
        assert!(count.checked_mul(size_of::<f32>()).unwrap() <= isize::MAX as usize);
        let mut output = FloatTensor::<Flex>::empty([m, n].into(), DType::F32);
        let y = output.storage_mut::<f32>();
        assert_eq!(y.len(), count);
        for i in 0..m {
            for j in 0..n {
                let b = bv[bo + j * bs[0]];
                assert!(b.is_finite(), "nonfinite bias");
                y[i * n + j] = b;
            }
        }
        // SAFETY: checked_view proves every x/weight read index and byte offset
        // is within its live immutable typed allocation, with nonnegative strides.
        // GEMM gets precisely those shapes/strides and existing Flex orientation.
        // Output is a fresh unique allocation, contiguous [m,n], so each write
        // is distinct and cannot alias any input. All count/offset arithmetic
        // is checked and fits isize. Every output is initialized before read_dst.
        // Borrowed slices keep all allocations alive for the synchronous call;
        // Parallelism::None introduces no concurrent writes or detached work.
        unsafe {
            gemm::gemm::<f32>(
                m,
                n,
                k,
                y.as_mut_ptr(),
                1,
                n as isize,
                true,
                xv.as_ptr().add(xo),
                xs[1] as isize,
                xs[0] as isize,
                wv.as_ptr().add(wo),
                ws[1] as isize,
                ws[0] as isize,
                1.0,
                1.0,
                false,
                false,
                false,
                gemm::Parallelism::None,
            );
        }
        assert!(
            y.iter().all(|v| v.is_finite()),
            "nonfinite fused linear output"
        );
        output
    }
}

#[derive(Debug)]
struct LinearBackward;
impl Backward<Flex, 3> for LinearBackward {
    type State = (FloatTensor<Flex>, FloatTensor<Flex>);
    fn backward(self, ops: Ops<Self::State, 3>, grads: &mut Gradients, _: &mut Checkpointer) {
        let (x, w) = ops.state;
        let grad = grads.consume::<Flex>(&ops.node);
        if let Some(parent) = &ops.parents[0] {
            grads.register::<Flex>(
                parent.id,
                Flex::float_matmul(grad.clone(), Flex::float_swap_dims(w, 0, 1)),
            );
        }
        if let Some(parent) = &ops.parents[1] {
            grads.register::<Flex>(
                parent.id,
                Flex::float_matmul(Flex::float_swap_dims(x, 0, 1), grad.clone()),
            );
        }
        if let Some(parent) = &ops.parents[2] {
            let n = grad.shape()[1];
            let db = Flex::float_reshape(Flex::float_sum_dim(grad, 0), [n].into());
            grads.register::<Flex>(parent.id, db);
        }
    }
}
impl<C: CheckpointStrategy> FusedLinearOps for Autodiff<Flex, C> {
    fn finite_fused_linear(
        x: FloatTensor<Self>,
        w: FloatTensor<Self>,
        b: FloatTensor<Self>,
    ) -> FloatTensor<Self> {
        let (x, xn) = x.into_parts();
        let (w, wn) = w.into_parts();
        let (b, bn) = b.into_parts();
        let prep = LinearBackward
            .prepare::<C>([xn, wn, bn])
            .compute_bound()
            .stateful();
        let output = Flex::finite_fused_linear(x.clone(), w.clone(), b);
        match prep {
            OpsKind::Tracked(prep) => prep.finish((x, w), output),
            OpsKind::UnTracked(prep) => prep.finish(output),
        }
    }
}

/// Compute x @ weight + bias; weight is [input,output], already transposed.
/// Positive rank/shape/dtype/context errors return Error. Unsupported primitive
/// strides/storage and nonfinite values panic before GEMM (or after for overflow).
/// Uses only public dispatch/reshape APIs; no host extraction or reinjection.
pub fn finite_fused_linear<const D: usize>(
    x: Tensor<D>,
    w: Tensor<2>,
    b: Tensor<1>,
) -> Result<Tensor<D>> {
    if D == 0 || x.dtype() != DType::F32 || w.dtype() != DType::F32 || b.dtype() != DType::F32 {
        return Err(Error::Input(
            "fused linear requires positive rank and f32".into(),
        ));
    }
    for mismatch in [
        x.device() != w.device(),
        x.device() != b.device(),
        x.is_autodiff() != w.is_autodiff(),
        x.is_autodiff() != b.is_autodiff(),
        x.device().gradient_checkpointing_strategy()
            != w.device().gradient_checkpointing_strategy(),
        x.device().gradient_checkpointing_strategy()
            != b.device().gradient_checkpointing_strategy(),
    ] {
        if mismatch {
            return Err(Error::Input(
                "fused linear needs one device/autodiff context".into(),
            ));
        }
    }
    let mut shape = x.dims();
    let k = shape[D - 1];
    let n = w.dims()[1];
    let rows = shape[..D - 1]
        .iter()
        .try_fold(1usize, |p, &n| p.checked_mul(n));
    let Some(rows) = rows else {
        return Err(Error::Input("fused linear shape overflow".into()));
    };
    if !(1..=120).contains(&rows)
        || !(1..=128).contains(&k)
        || !(1..=128).contains(&n)
        || w.dims()[0] != k
        || b.dims() != [n]
    {
        return Err(Error::Input(
            "fused linear incompatible/oversize/empty shape".into(),
        ));
    }
    shape[D - 1] = n;
    let output = Dispatch::finite_fused_linear(
        x.reshape([rows, k]).into_dispatch(),
        w.into_dispatch(),
        b.into_dispatch(),
    );
    Ok(Tensor::<2>::from_dispatch(output).reshape(shape))
}
