//! Finite same-input ff.2 diagnosis; no full model forward or learning.
use banto_ai::checkpoint::sha256;
use burn::tensor::{Device, Tensor, TensorData};
use serde::Deserialize;
use serde_json::json;
use std::{collections::BTreeMap, env, fs, io::Write, path::Path};
#[derive(Deserialize)]
struct Entry {
    shape: Vec<usize>,
    offset_bytes: usize,
    length_bytes: usize,
}
#[derive(Deserialize)]
struct Manifest {
    schema: String,
    payload_sha256: String,
    tensors: BTreeMap<String, Entry>,
}
fn write(path: &Path, bytes: &[u8]) {
    fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .unwrap()
        .write_all(bytes)
        .unwrap();
}
fn main() {
    let a: Vec<String> = env::args().skip(1).collect();
    assert_eq!(
        a.len(),
        4,
        "MANIFEST PAYLOAD TRUSTED_MANIFEST_SHA NEW_OUTPUT_DIR"
    );
    let m = fs::read(&a[0]).unwrap();
    let raw = fs::read(&a[1]).unwrap();
    assert!(m.len() < 256 * 1024 && raw.len() < 32 * 1024 * 1024);
    assert_eq!(sha256(&m), a[2]);
    let m: Manifest = serde_json::from_slice(&m).unwrap();
    assert_eq!(m.schema, "banto.r1-ff-diagnosis.v1");
    assert_eq!(sha256(&raw), m.payload_sha256);
    let device = Device::flex();
    let values = |name: &str, shape: &[usize]| {
        let e = &m.tensors[name];
        assert_eq!(e.shape, shape);
        assert_eq!(e.length_bytes, shape.iter().product::<usize>() * 4);
        let end = e.offset_bytes.checked_add(e.length_bytes).unwrap();
        assert!(end <= raw.len());
        raw[e.offset_bytes..end]
            .chunks_exact(4)
            .map(|b| f32::from_le_bytes(b.try_into().unwrap()))
            .collect::<Vec<_>>()
    };
    let weight = Tensor::<2>::from_data(
        TensorData::new(values("weight", &[64, 128]), [64, 128]),
        &device,
    )
    .transpose();
    let bias = Tensor::<2>::from_data(TensorData::new(values("bias", &[64]), [1, 64]), &device);
    let mut outputs = BTreeMap::new();
    for side in ["python", "rust"] {
        let x = Tensor::<2>::from_data(
            TensorData::new(
                values(&format!("{side}_input"), &[8, 3, 5, 128]),
                [120, 128],
            ),
            &device,
        );
        let residual = Tensor::<2>::from_data(
            TensorData::new(
                values(&format!("{side}_residual"), &[8, 3, 5, 64]),
                [120, 64],
            ),
            &device,
        );
        // Match SmallForecaster::linear: canonical [out,in] transposed, matmul then bias.
        let linear = x.matmul(weight.clone()) + bias.clone();
        let block = residual + linear.clone();
        for (suffix, t) in [("flex_linear", linear), ("flex_block", block)] {
            let v = t.to_data().to_vec::<f32>().unwrap();
            assert!(v.iter().all(|v| v.is_finite()));
            outputs.insert(format!("{side}_{suffix}"), v);
        }
    }
    let out = Path::new(&a[3]);
    fs::create_dir(out).unwrap();
    let result = serde_json::to_vec(&outputs).unwrap();
    write(&out.join("outputs.json"), &result);
    let summary = serde_json::to_vec(
        &json!({"full_forward_calls":0,"linear_calls":2,"training":false,"manifest_sha256":a[2]}),
    )
    .unwrap();
    write(&out.join("summary.json"), &summary);
    write(
        &out.join("root-closed.json"),
        &serde_json::to_vec(&json!({"status":"complete","files":[
        {"name":"outputs.json","bytes":result.len(),"sha256":sha256(&result)},
        {"name":"summary.json","bytes":summary.len(),"sha256":sha256(&summary)}]}))
        .unwrap(),
    );
    println!("{}", json!({"status":"complete","linear_calls":2}));
}
