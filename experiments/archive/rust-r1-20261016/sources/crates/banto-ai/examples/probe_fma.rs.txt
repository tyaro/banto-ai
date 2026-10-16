//! Frozen artificial forward/graph routing checks, never backward or training.
use banto_ai::{checkpoint::sha256, fma::finite_fma};
use burn::tensor::{Device, FloatDType, Tensor, TensorData};
use serde::Deserialize;
use serde_json::json;
use std::{env, fs, io::Write, panic::AssertUnwindSafe, path::Path};

#[derive(Deserialize)]
struct Row {
    name: String,
    a: u32,
    b: u32,
    c: u32,
    expected: u32,
}
#[derive(Deserialize)]
struct Fixture {
    schema: String,
    cases: Vec<Row>,
}
fn bits<const D: usize>(x: Tensor<D>) -> Vec<u32> {
    x.into_data()
        .to_vec::<f32>()
        .unwrap()
        .into_iter()
        .map(f32::to_bits)
        .collect()
}
fn tensor<const D: usize>(v: Vec<f32>, shape: [usize; D], d: &Device) -> Tensor<D> {
    Tensor::from_data(TensorData::new(v, shape), d)
}
fn write(p: &Path, data: &[u8]) {
    fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)
        .unwrap()
        .write_all(data)
        .unwrap();
}
fn main() {
    let args: Vec<_> = env::args().skip(1).collect();
    assert_eq!(args.len(), 3, "FIXTURE TRUSTED_SHA NEW_OUTPUT");
    let raw = fs::read(&args[0]).unwrap();
    assert!(raw.len() < 64 * 1024);
    assert_eq!(sha256(&raw), args[1]);
    let f: Fixture = serde_json::from_slice(&raw).unwrap();
    assert_eq!(f.schema, "banto.fma-forward-fixture.v1");
    assert_eq!(f.cases.len(), 20);
    let mut reports = Vec::new();
    let expected: Vec<_> = f.cases.iter().map(|r| r.expected).collect();
    for r in &f.cases {
        assert_eq!(
            f32::from_bits(r.a)
                .mul_add(f32::from_bits(r.b), f32::from_bits(r.c))
                .to_bits(),
            r.expected,
            "scalar {}",
            r.name
        );
    }
    let plain = Device::flex();
    let ad = Device::flex().autodiff();
    for (name, device) in [("plain", &plain), ("autodiff", &ad)] {
        let get = |which: usize| {
            tensor(
                f.cases
                    .iter()
                    .map(|r| f32::from_bits([r.a, r.b, r.c][which]))
                    .collect(),
                [20],
                device,
            )
        };
        let a = if name == "autodiff" {
            get(0).require_grad()
        } else {
            get(0)
        };
        let before = bits(a.clone());
        let y = finite_fma(a.clone(), get(1), get(2)).unwrap();
        assert_eq!(y.is_tracked(), name == "autodiff");
        assert_eq!(bits(y), expected);
        assert_eq!(bits(a), before);
        reports.push(json!({"path":name,"elements":20,"expected_bits_match":true,"tracked":name=="autodiff"}));
    }
    let a = tensor(vec![1., 2.], [2, 1], &ad).require_grad();
    let b = tensor(vec![3., 4., 5.], [1, 3], &ad);
    let c = tensor(vec![1.], [1, 1], &ad);
    let y = finite_fma(a, b, c).unwrap();
    assert!(y.is_tracked());
    assert_eq!(bits(y), [4., 5., 6., 7., 9., 11.].map(f32::to_bits));
    let x = tensor(vec![1., 2., 3., 4., 5., 6.], [2, 3], &ad)
        .require_grad()
        .swap_dims(0, 1);
    let y = finite_fma(x.clone(), x.clone(), x.clone()).unwrap();
    assert!(y.is_tracked());
    assert_eq!(bits(y), [2., 20., 6., 30., 12., 42.].map(f32::to_bits));
    assert_eq!(bits(x), [1., 4., 2., 5., 3., 6.].map(f32::to_bits));
    let x = tensor(vec![99., 1., 2., 3., 4., 88.], [6], &plain).slice([1..5]);
    assert_eq!(
        bits(finite_fma(x.clone(), x.clone(), x).unwrap()),
        [2., 6., 12., 20.].map(f32::to_bits)
    );
    assert!(
        finite_fma(
            tensor(vec![1.; 2], [2], &plain),
            tensor(vec![1.; 3], [3], &plain),
            tensor(vec![0.], [1], &plain)
        )
        .is_err()
    );
    assert!(
        finite_fma(
            tensor(vec![1.], [1], &plain).cast(FloatDType::F64),
            tensor(vec![1.], [1], &plain),
            tensor(vec![1.], [1], &plain)
        )
        .is_err()
    );
    assert!(
        finite_fma(
            tensor(vec![], [0], &plain),
            tensor(vec![1.], [1], &plain),
            tensor(vec![0.], [1], &plain)
        )
        .is_err()
    );
    assert!(
        finite_fma(
            tensor(vec![1.], [1], &plain),
            tensor(vec![1.], [1], &ad),
            tensor(vec![1.], [1], &plain)
        )
        .is_err()
    );
    for (a, b, c) in [
        (f32::NAN, 1., 0.),
        (f32::INFINITY, 1., 0.),
        (f32::MAX, 2., 0.),
    ] {
        assert!(
            std::panic::catch_unwind(AssertUnwindSafe(|| finite_fma(
                tensor(vec![a], [1], &plain),
                tensor(vec![b], [1], &plain),
                tensor(vec![c], [1], &plain)
            )))
            .is_err()
        );
    }
    let result = json!({"scalar_oracle_rows":20,"plain_bits":20,"autodiff_bits":20,"broadcast_elements":6,"view_alias_elements":6,"offset_elements":4,"boundary_rejections":7,"input_unchanged":true,"tracked_output":true,"backward_calls":0,"model_forward":0,"training":false,"reports":reports});
    let bytes = serde_json::to_vec(&result).unwrap();
    let p = Path::new(&args[2]);
    fs::create_dir(p).unwrap();
    write(&p.join("summary.json"), &bytes);
    write(&p.join("root-closed.json"),&serde_json::to_vec(&json!({"status":"complete","files":[{"name":"summary.json","bytes":bytes.len(),"sha256":sha256(&bytes)}]})).unwrap());
    println!("{}", result);
}
