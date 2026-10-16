//! Fixed exact artificial outputs, graph/alias and boundary checks; no backward.
use banto_ai::{checkpoint::sha256, fused_linear::finite_fused_linear};
use burn::tensor::{Device, FloatDType, Tensor, TensorData};
use serde::Deserialize;
use serde_json::json;
use std::{env, fs, io::Write, panic::AssertUnwindSafe, path::Path};
#[derive(Deserialize)]
struct Case {
    name: String,
    shape: [usize; 3],
    x: Vec<f32>,
    weight: Vec<f32>,
    bias: Vec<f32>,
    layout: String,
    expected_bits: Vec<u32>,
}
#[derive(Deserialize)]
struct Fixture {
    schema: String,
    cases: Vec<Case>,
}
fn tensor<const D: usize>(v: Vec<f32>, shape: [usize; D], device: &Device) -> Tensor<D> {
    Tensor::from_data(TensorData::new(v, shape), device)
}
fn bits<const D: usize>(t: Tensor<D>) -> Vec<u32> {
    t.to_data()
        .to_vec::<f32>()
        .unwrap()
        .into_iter()
        .map(f32::to_bits)
        .collect()
}
fn write(p: &Path, v: &[u8]) {
    fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)
        .unwrap()
        .write_all(v)
        .unwrap();
}
fn main() {
    let a: Vec<String> = env::args().skip(1).collect();
    assert_eq!(a.len(), 3, "FIXTURE TRUSTED_SHA NEW_ROOT");
    assert!(fs::metadata(&a[0]).unwrap().len() < 64 * 1024);
    let raw = fs::read(&a[0]).unwrap();
    assert_eq!(sha256(&raw), a[1]);
    let f: Fixture = serde_json::from_slice(&raw).unwrap();
    assert_eq!(f.schema, "banto.fused-linear-artificial.v1");
    assert_eq!(f.cases.len(), 8);
    let plain = Device::flex();
    let ad = Device::flex().autodiff();
    let mut rows = Vec::new();
    let mut count = 0;
    for (path, device) in [("plain", &plain), ("autodiff", &ad)] {
        for c in &f.cases {
            let [m, k, n] = c.shape;
            let x = if c.layout == "offset" {
                let mut v = vec![97.; k];
                v.extend_from_slice(&c.x);
                v.extend(vec![99.; k]);
                tensor(v, [m + 2, k], device).slice([1..m + 1, 0..k])
            } else {
                tensor(c.x.clone(), [m, k], device)
            };
            let w = if c.layout == "transpose" {
                let v = (0..n)
                    .flat_map(|j| (0..k).map(move |i| c.weight[i * n + j]))
                    .collect();
                tensor(v, [n, k], device).transpose()
            } else {
                tensor(c.weight.clone(), [k, n], device)
            };
            let b = tensor(c.bias.clone(), [n], device);
            let (x, w, b) = if path == "autodiff" {
                (x.require_grad(), w.require_grad(), b.require_grad())
            } else {
                (x, w, b)
            };
            let before = (bits(x.clone()), bits(w.clone()), bits(b.clone()));
            let y = finite_fused_linear(x.clone(), w.clone(), b.clone()).unwrap();
            assert_eq!(y.is_tracked(), path == "autodiff");
            assert_eq!(bits(y), c.expected_bits, "{} {}", path, c.name);
            assert_eq!(before, (bits(x), bits(w), bits(b)));
            count += c.expected_bits.len();
            rows.push(json!({"path":path,"case":c.name,"bits_exact":true,"tracked":path=="autodiff","input_unchanged":true}));
        }
    }
    let c = &f.cases[0];
    let [m, k, n] = c.shape;
    for parent in 0..3 {
        let x = tensor(c.x.clone(), [m, k], &ad);
        let w = tensor(c.weight.clone(), [k, n], &ad);
        let b = tensor(c.bias.clone(), [n], &ad);
        let x = if parent == 0 { x.require_grad() } else { x };
        let w = if parent == 1 { w.require_grad() } else { w };
        let b = if parent == 2 { b.require_grad() } else { b };
        let y = finite_fused_linear(x, w, b).unwrap();
        assert!(y.is_tracked());
        assert_eq!(bits(y), c.expected_bits);
    }
    let y = finite_fused_linear(
        tensor(c.x.clone(), [1, 1, m, k], &ad).require_grad(),
        tensor(c.weight.clone(), [k, n], &ad),
        tensor(c.bias.clone(), [n], &ad),
    )
    .unwrap();
    assert_eq!(y.dims(), [1, 1, m, n]);
    assert!(y.is_tracked());
    assert_eq!(bits(y), c.expected_bits);
    let mut rejected = 0;
    macro_rules! reject {
        ($value:expr) => {{
            let r = std::panic::catch_unwind(AssertUnwindSafe(|| $value));
            assert!(
                match r {
                    Err(_) => true,
                    Ok(v) => v.is_err(),
                },
                "boundary was accepted"
            );
            rejected += 1;
        }};
    }
    let x = || Tensor::<2>::ones([2, 2], &plain);
    let w = || Tensor::<2>::ones([2, 2], &plain);
    let b = || Tensor::<1>::ones([2], &plain);
    reject!(finite_fused_linear(
        x(),
        Tensor::<2>::ones([3, 2], &plain),
        b()
    ));
    reject!(finite_fused_linear(
        x(),
        w(),
        Tensor::<1>::ones([3], &plain)
    ));
    reject!(finite_fused_linear(
        Tensor::<2>::zeros([0, 2], &plain),
        w(),
        b()
    ));
    reject!(finite_fused_linear(x(), w().cast(FloatDType::F64), b()));
    reject!(finite_fused_linear(
        x(),
        Tensor::<2>::ones([2, 2], &ad),
        b()
    ));
    reject!(finite_fused_linear(
        Tensor::<2>::ones([121, 2], &plain),
        w(),
        b()
    ));
    reject!(finite_fused_linear(
        Tensor::<2>::ones([2, 129], &plain),
        Tensor::<2>::ones([129, 2], &plain),
        b()
    ));
    reject!(finite_fused_linear(
        x(),
        Tensor::<2>::ones([2, 129], &plain),
        Tensor::<1>::ones([129], &plain)
    ));
    reject!(finite_fused_linear(
        tensor(vec![f32::NAN; 4], [2, 2], &plain),
        w(),
        b()
    ));
    reject!(finite_fused_linear(
        x(),
        tensor(vec![f32::INFINITY; 4], [2, 2], &plain),
        b()
    ));
    reject!(finite_fused_linear(
        x(),
        w(),
        tensor(vec![f32::NEG_INFINITY; 2], [2], &plain)
    ));
    reject!(finite_fused_linear(
        tensor(vec![f32::MAX], [1, 1], &plain),
        tensor(vec![2.], [1, 1], &plain),
        tensor(vec![0.], [1], &plain)
    ));
    reject!(finite_fused_linear(x(), w().flip([0]), b()));
    assert_eq!(rejected, 13);
    let summary = json!({"artificial_cases":8,"paths":2,"exact_elements":count,"parent_only_graph_routes":3,"high_rank_wrapper":true,"boundary_rejections":rejected,"input_unchanged":true,"backward_calls":0,"full_forward":0,"training":false,"reports":rows});
    let out = Path::new(&a[2]);
    fs::create_dir(out).unwrap();
    let bytes = serde_json::to_vec(&summary).unwrap();
    write(&out.join("summary.json"), &bytes);
    write(&out.join("root-closed.json"),&serde_json::to_vec(&json!({"status":"complete","files":[{"name":"summary.json","bytes":bytes.len(),"sha256":sha256(&bytes)}]})).unwrap());
    println!("{summary}");
}
