//! Opt-in finite f32 FMA through Burn's public Flex/autodiff extension boundary.
//! Forward is verified separately from the pending R2 gradient checks.
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
trait FmaOps: Backend {
    fn finite_fma(
        a: FloatTensor<Self>,
        b: FloatTensor<Self>,
        c: FloatTensor<Self>,
    ) -> FloatTensor<Self>;
}

impl FmaOps for Flex {
    fn finite_fma(
        a: FloatTensor<Self>,
        b: FloatTensor<Self>,
        c: FloatTensor<Self>,
    ) -> FloatTensor<Self> {
        assert!(a.dtype() == DType::F32 && b.dtype() == DType::F32 && c.dtype() == DType::F32);
        assert_eq!(a.shape(), b.shape());
        assert_eq!(a.shape(), c.shape());
        let (a, b, c) = (a.to_contiguous(), b.to_contiguous(), c.to_contiguous());
        let n = a.layout().num_elements();
        let slice = |x: &FloatTensor<Flex>| {
            let start = x.layout().start_offset();
            (start, start + n)
        };
        let (ai, ae) = slice(&a);
        let (bi, be) = slice(&b);
        let (ci, ce) = slice(&c);
        let av = &a.storage::<f32>()[ai..ae];
        let bv = &b.storage::<f32>()[bi..be];
        let cv = &c.storage::<f32>()[ci..ce];
        let mut output = FloatTensor::<Flex>::empty(a.shape(), DType::F32);
        for (((dst, a), b), c) in output
            .storage_mut::<f32>()
            .iter_mut()
            .zip(av)
            .zip(bv)
            .zip(cv)
        {
            assert!(
                a.is_finite() && b.is_finite() && c.is_finite(),
                "FMA input must be finite"
            );
            *dst = a.mul_add(*b, *c);
            assert!(dst.is_finite(), "FMA result must be finite");
        }
        output
    }
}

#[derive(Debug)]
struct FmaBackward;

impl Backward<Flex, 3> for FmaBackward {
    type State = (FloatTensor<Flex>, FloatTensor<Flex>);

    fn backward(
        self,
        ops: Ops<Self::State, 3>,
        grads: &mut Gradients,
        _checkpointer: &mut Checkpointer,
    ) {
        let (a, b) = ops.state;
        let grad = grads.consume::<Flex>(&ops.node);
        // Expand is recorded before this node, so its backward sums broadcast axes.
        // Register each parent independently: aliasing contributes to the same node.
        if let Some(parent) = &ops.parents[0] {
            grads.register::<Flex>(parent.id, Flex::float_mul(grad.clone(), b));
        }
        if let Some(parent) = &ops.parents[1] {
            grads.register::<Flex>(parent.id, Flex::float_mul(grad.clone(), a));
        }
        if let Some(parent) = &ops.parents[2] {
            grads.register::<Flex>(parent.id, grad);
        }
    }
}

impl<C: CheckpointStrategy> FmaOps for Autodiff<Flex, C> {
    fn finite_fma(
        a: FloatTensor<Self>,
        b: FloatTensor<Self>,
        c: FloatTensor<Self>,
    ) -> FloatTensor<Self> {
        let (a, an) = a.into_parts();
        let (b, bn) = b.into_parts();
        let (c, cn) = c.into_parts();
        // Keep guards alive until finish registers the custom child, then release.
        let prep = FmaBackward
            .prepare::<C>([an, bn, cn])
            .compute_bound()
            .stateful();
        let output = Flex::finite_fma(a.clone(), b.clone(), c);
        match prep {
            OpsKind::Tracked(prep) => prep.finish((a, b), output),
            OpsKind::UnTracked(prep) => prep.finish(output),
        }
    }
}

/// Finite f32 fused multiply-add with same-rank positive-dimension broadcasting.
///
/// Shape/dtype/device mismatches return an error. Nonfinite inputs or results
/// panic at the low-level kernel boundary. No high-level host tensor extraction
/// or reinjection occurs. Backward code is present but awaits the R2 checks.
pub fn finite_fma<const D: usize>(a: Tensor<D>, b: Tensor<D>, c: Tensor<D>) -> Result<Tensor<D>> {
    if a.dtype() != DType::F32 || b.dtype() != DType::F32 || c.dtype() != DType::F32 {
        return Err(Error::Input("FMA requires f32 operands".into()));
    }
    if a.device() != b.device()
        || a.device() != c.device()
        || a.is_autodiff() != b.is_autodiff()
        || a.is_autodiff() != c.is_autodiff()
        || a.device().gradient_checkpointing_strategy()
            != b.device().gradient_checkpointing_strategy()
        || a.device().gradient_checkpointing_strategy()
            != c.device().gradient_checkpointing_strategy()
    {
        return Err(Error::Input(
            "FMA operands require one device/autodiff context".into(),
        ));
    }
    if D == 0 {
        return Err(Error::Input("FMA requires positive rank".into()));
    }
    let shapes = [a.dims(), b.dims(), c.dims()];
    let mut shape = [1; D];
    for axis in 0..D {
        for dims in &shapes {
            let n = dims[axis];
            if n == 0 || (shape[axis] != 1 && n != 1 && n != shape[axis]) {
                return Err(Error::Input("incompatible FMA broadcast dimensions".into()));
            }
            shape[axis] = shape[axis].max(n);
        }
    }
    let output = Dispatch::finite_fma(
        a.expand(shape).into_dispatch(),
        b.expand(shape).into_dispatch(),
        c.expand(shape).into_dispatch(),
    );
    Ok(Tensor::from_dispatch(output))
}

/// Width-64 LayerNorm in the binary-confirmed four-lane CPU reference order.
/// Tensor slices and public FMA nodes preserve the future training graph.
pub fn reference_layer_norm<const D: usize>(
    x: Tensor<D>,
    gamma: Tensor<1>,
    beta: Tensor<1>,
) -> Tensor<D> {
    let shape = x.dims();
    assert_eq!(shape[D - 1], 64);
    let rows = shape.iter().product::<usize>() / 64;
    let device = x.device();
    let flat = x.reshape([rows, 64]);
    let chunks = flat.clone().reshape([rows, 16, 4]);
    let mut means = Tensor::<2>::zeros([rows, 4], &device);
    let mut m2s = Tensor::<2>::zeros([rows, 4], &device);
    let fma = |a, b, c| finite_fma(a, b, c).expect("internal finite f32 LayerNorm invariant");
    for step in 0..16 {
        let row = chunks
            .clone()
            .slice([0..rows, step..step + 1, 0..4])
            .reshape([rows, 4]);
        let c = Tensor::<2>::full([1, 1], 1.0f32 / (step + 1) as f32, &device);
        let delta = row.clone() - means.clone();
        means = fma(c, delta.clone(), means);
        m2s = fma(delta, row - means.clone(), m2s);
    }
    // The source's vector merge into the zero-count initial stack.
    let zero4 = Tensor::<2>::zeros([rows, 4], &device);
    let delta = means;
    means = zero4.clone() + delta.clone();
    m2s = fma(delta.clone() * 0.0, delta, zero4 + m2s);
    let mut mu = Tensor::<2>::zeros([rows, 1], &device);
    let mut m2 = Tensor::<2>::zeros([rows, 1], &device);
    for lane in 0..4 {
        let n = (lane * 16) as f32;
        let c = 16.0f32 / (n + 16.0);
        let delta = means.clone().slice([0..rows, lane..lane + 1]) - mu.clone();
        let lane_m2 = m2s.clone().slice([0..rows, lane..lane + 1]);
        let cross = delta.clone().square() * c;
        m2 = m2 + fma(cross, Tensor::full([1, 1], n, &device), lane_m2);
        mu = fma(Tensor::full([1, 1], c, &device), delta, mu);
    }
    let inv = (m2 / 64.0 + 1e-5).sqrt().recip();
    ((flat - mu) * inv * gamma.reshape([1, 64]) + beta.reshape([1, 64])).reshape(shape)
}
