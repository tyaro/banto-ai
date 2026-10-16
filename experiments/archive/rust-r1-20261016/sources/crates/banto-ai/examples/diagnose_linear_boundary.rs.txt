//! Seven frozen patch boundaries: current matmul and isolated bias addition.
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
struct Case {
    id: String,
    batch: usize,
}
#[derive(Deserialize)]
struct Manifest {
    schema: String,
    cases: Vec<Case>,
    tensors: BTreeMap<String, Entry>,
    payload_sha256: String,
}
fn values(raw: &[u8], e: &Entry) -> Vec<f32> {
    assert_eq!(e.shape.iter().product::<usize>() * 4, e.length_bytes);
    let end = e.offset_bytes.checked_add(e.length_bytes).unwrap();
    assert!(end <= raw.len());
    raw[e.offset_bytes..end]
        .chunks_exact(4)
        .map(|v| f32::from_le_bytes(v.try_into().unwrap()))
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
    assert_eq!(a.len(), 4, "MANIFEST DATA TRUSTED_SHA NEW_ROOT");
    assert!(fs::metadata(&a[0]).unwrap().len() < 256 * 1024);
    assert!(fs::metadata(&a[1]).unwrap().len() < 32 * 1024 * 1024);
    let mr = fs::read(&a[0]).unwrap();
    assert_eq!(sha256(&mr), a[2]);
    let m: Manifest = serde_json::from_slice(&mr).unwrap();
    assert_eq!(m.schema, "banto.r1-linear-boundary.v1");
    assert_eq!(m.cases.len(), 7);
    let input = fs::read(&a[1]).unwrap();
    assert_eq!(sha256(&input), m.payload_sha256);
    let device = Device::flex();
    let w = Tensor::<2>::from_data(
        TensorData::new(values(&input, &m.tensors["weight/patch.weight"]), [64, 32]),
        &device,
    )
    .transpose();
    let bias = Tensor::<2>::from_data(
        TensorData::new(values(&input, &m.tensors["weight/patch.bias"]), [1, 64]),
        &device,
    );
    let mut raw = Vec::new();
    let mut entries = BTreeMap::new();
    for c in &m.cases {
        let rows = c.batch * 12;
        assert!((1..=8).contains(&c.batch));
        let x = Tensor::<2>::from_data(
            TensorData::new(
                values(&input, &m.tensors[&format!("{}/input", c.id)]),
                [rows, 32],
            ),
            &device,
        );
        let pm = Tensor::<2>::from_data(
            TensorData::new(
                values(&input, &m.tensors[&format!("{}/python/mm", c.id)]),
                [rows, 64],
            ),
            &device,
        );
        let mm = x.matmul(w.clone());
        let own = mm.clone() + bias.clone();
        let same = pm + bias.clone();
        for (kind, t) in [("mm", mm), ("own_add", own), ("python_mm_add", same)] {
            let v = t.to_data().to_vec::<f32>().unwrap();
            assert!(v.iter().all(|v| v.is_finite()));
            let start = raw.len();
            for v in v {
                raw.extend_from_slice(&v.to_le_bytes());
            }
            entries.insert(format!("{}/rust/{kind}",c.id),json!({"shape":[c.batch,3,4,64],"offset_bytes":start,"length_bytes":raw.len()-start}));
        }
    }
    assert_eq!(entries.len(), 21);
    let p = Path::new(&a[3]);
    fs::create_dir(p).unwrap();
    write(&p.join("tensors.bin"), &raw);
    let manifest=serde_json::to_vec(&json!({"schema":"banto.r1-linear-kernel.v1","tensors":entries,"fixture_manifest_sha256":a[2],"payload_sha256":sha256(&raw)})).unwrap();
    write(&p.join("manifest.json"), &manifest);
    let files = [("tensors.bin", &raw), ("manifest.json", &manifest)]
        .into_iter()
        .map(|(name, v)| json!({"name":name,"bytes":v.len(),"sha256":sha256(v)}))
        .collect::<Vec<_>>();
    write(
        &p.join("root-closed.json"),
        &serde_json::to_vec(&json!({"status":"complete","files":files})).unwrap(),
    );
    println!(
        "{}",
        json!({"matmul_calls":7,"own_bias_add_calls":7,"same_input_bias_add_calls":7,"full_forward":0,"model_changed":false,"training":false})
    );
}
