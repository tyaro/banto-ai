//! One source-ordered context diagnostic: plain/AD candidate and old baseline.
use banto_ai::{checkpoint::sha256, context::reference_context};
use burn::tensor::{Device, Tensor, TensorData};
use serde::Deserialize;
use serde_json::json;
use std::{collections::BTreeMap, env, fs, io::Write, path::Path};

#[derive(Deserialize)]
struct Case {
    id: String,
    batch: usize,
    offset_bytes: usize,
    length_bytes: usize,
}
#[derive(Deserialize)]
struct Floors {
    floors: Vec<f32>,
}
#[derive(Deserialize)]
struct Fixture {
    schema: String,
    inputs_sha256: String,
    cases: Vec<Case>,
    floor_certificates: BTreeMap<String, Floors>,
}
fn mean(x: Tensor<3>) -> Tensor<3> {
    let [b, s, mut n] = x.dims();
    let mut v = x.reshape([b * s, n]);
    while n > 1 {
        v = v
            .reshape([b * s, n / 2, 2])
            .sum_dim(2)
            .reshape([b * s, n / 2]);
        n /= 2;
    }
    (v / 128.0).reshape([b, s, 1])
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
    assert_eq!(
        a.len(),
        6,
        "FIXTURE INPUT FIXTURE_SHA CONTEXT_MANIFEST CONTEXT_SHA NEW_ROOT"
    );
    assert!(fs::metadata(&a[0]).unwrap().len() < 256 * 1024);
    assert!(fs::metadata(&a[1]).unwrap().len() < 32 * 1024 * 1024);
    assert!(fs::metadata(&a[3]).unwrap().len() < 256 * 1024);
    let manifest = fs::read(&a[0]).unwrap();
    assert_eq!(sha256(&manifest), a[2]);
    let f: Fixture = serde_json::from_slice(&manifest).unwrap();
    assert_eq!(f.schema, "banto.r1-forward-fixtures.v1");
    assert_eq!(f.cases.len(), 7);
    let input = fs::read(&a[1]).unwrap();
    assert_eq!(sha256(&input), f.inputs_sha256);
    assert_eq!(sha256(&fs::read(&a[3]).unwrap()), a[4]);
    let floor = &f.floor_certificates["floor-equal"].floors;
    assert_eq!(floor.len(), 3);
    let plain = Device::flex();
    let ad = Device::flex().autodiff();
    let mut raw = Vec::new();
    let mut entries = BTreeMap::new();
    let mut tracked = 0;
    for c in &f.cases {
        assert_eq!(c.length_bytes, c.batch * 3 * 128 * 4);
        let end = c.offset_bytes.checked_add(c.length_bytes).unwrap();
        assert!(end <= input.len());
        let values: Vec<f32> = input[c.offset_bytes..end]
            .chunks_exact(4)
            .map(|v| f32::from_le_bytes(v.try_into().unwrap()))
            .collect();
        for (kind, device) in [("baseline", &plain), ("plain", &plain), ("autodiff", &ad)] {
            let x =
                Tensor::<3>::from_data(TensorData::new(values.clone(), [c.batch, 3, 128]), device);
            let x = if kind == "autodiff" {
                x.require_grad()
            } else {
                x
            };
            let before = x.to_data().to_vec::<f32>().unwrap();
            let floor = Tensor::<3>::from_data(TensorData::new(floor.clone(), [1, 3, 1]), device);
            let (mu, std, scale, norm) = if kind == "baseline" {
                let mu = mean(x.clone());
                let center = x.clone() - mu.clone();
                let std = mean(center.clone().square()).sqrt();
                let scale = std.clone().max_pair(floor);
                let norm = center / scale.clone();
                (mu, std, scale, norm)
            } else {
                reference_context(x.clone(), floor)
            };
            assert_eq!(
                before.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                x.to_data()
                    .to_vec::<f32>()
                    .unwrap()
                    .iter()
                    .map(|v| v.to_bits())
                    .collect::<Vec<_>>()
            );
            for (name, tensor) in [
                ("context_center", mu),
                ("raw_std", std),
                ("context_scale", scale),
                ("normalized_context", norm),
            ] {
                assert_eq!(tensor.is_tracked(), kind == "autodiff");
                if tensor.is_tracked() {
                    tracked += 1;
                }
                let shape = tensor.dims().to_vec();
                let v = tensor.to_data().to_vec::<f32>().unwrap();
                assert!(v.iter().all(|x| x.is_finite()));
                let start = raw.len();
                for x in v {
                    raw.extend_from_slice(&x.to_le_bytes());
                }
                entries.insert(
                    format!("{}/{kind}/{name}", c.id),
                    json!({"shape":shape,"offset_bytes":start,"length_bytes":raw.len()-start}),
                );
            }
        }
    }
    assert_eq!(tracked, 28);
    assert_eq!(entries.len(), 84);
    let p = Path::new(&a[5]);
    fs::create_dir(p).unwrap();
    write(&p.join("tensors.bin"), &raw);
    let m=serde_json::to_vec(&json!({"schema":"banto.r1-context-kernel.v1","tensors":entries,"fixture_manifest_sha256":a[4],"payload_sha256":sha256(&raw)})).unwrap();
    write(&p.join("manifest.json"), &m);
    let summary=serde_json::to_vec(&json!({"tracked_outputs":tracked,"input_unchanged":true,"backward_calls":0,"full_forward":0,"training":false})).unwrap();
    write(&p.join("summary.json"), &summary);
    let files = [
        ("tensors.bin", &raw),
        ("manifest.json", &m),
        ("summary.json", &summary),
    ]
    .into_iter()
    .map(|(name, v)| json!({"name":name,"bytes":v.len(),"sha256":sha256(v)}))
    .collect::<Vec<_>>();
    write(
        &p.join("root-closed.json"),
        &serde_json::to_vec(&json!({"status":"complete","files":files})).unwrap(),
    );
    println!("{}", String::from_utf8(summary).unwrap());
}
