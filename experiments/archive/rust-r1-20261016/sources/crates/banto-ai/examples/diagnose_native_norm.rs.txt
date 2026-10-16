//! One preregistered standard-operator candidate, all seven cases and norms.
use banto_ai::checkpoint::sha256;
use burn::tensor::{Device, Tensor, TensorData, module};
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
    payload_sha256: String,
    cases: Vec<Case>,
    tensors: BTreeMap<String, Entry>,
}
fn values(raw: &[u8], e: &Entry) -> Vec<f32> {
    assert_eq!(e.length_bytes, e.shape.iter().product::<usize>() * 4);
    raw[e.offset_bytes..e.offset_bytes.checked_add(e.length_bytes).unwrap()]
        .chunks_exact(4)
        .map(|v| f32::from_le_bytes(v.try_into().unwrap()))
        .collect()
}
fn mean(x: Tensor<2>) -> Tensor<2> {
    let [rows, mut n] = x.dims();
    let width = n;
    let mut x = x;
    assert_eq!(width, 64);
    while n > 1 {
        x = x
            .reshape([rows, n / 2, 2])
            .sum_dim(2)
            .reshape([rows, n / 2]);
        n /= 2;
    }
    x / width as f32
}
fn write(p: &Path, raw: &[u8]) {
    fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)
        .unwrap()
        .write_all(raw)
        .unwrap();
}
fn main() {
    let a: Vec<String> = env::args().skip(1).collect();
    assert_eq!(a.len(), 4, "MANIFEST DATA TRUSTED_SHA NEW_OUTPUT");
    assert!(fs::metadata(&a[0]).unwrap().len() < 256 * 1024);
    assert!(fs::metadata(&a[1]).unwrap().len() < 32 * 1024 * 1024);
    let m = fs::read(&a[0]).unwrap();
    assert_eq!(sha256(&m), a[2]);
    let m: Manifest = serde_json::from_slice(&m).unwrap();
    assert_eq!(m.schema, "banto.r1-all-layer-audit.v1");
    assert_eq!(m.cases.len(), 7);
    let raw = fs::read(&a[1]).unwrap();
    assert_eq!(sha256(&raw), m.payload_sha256);
    let device = Device::flex();
    let mut output = Vec::new();
    let mut entries = BTreeMap::new();
    for case in &m.cases {
        for index in 0..7 {
            let (name, source) = if index < 6 {
                let block = index / 3;
                let norm = index % 3;
                let input = match norm {
                    0 => {
                        if block == 0 {
                            "tokens".into()
                        } else {
                            "blocks.0".into()
                        }
                    }
                    1 => format!("blocks.{block}.residual0"),
                    _ => format!("blocks.{block}.residual1"),
                };
                (format!("blocks.{block}.norms.{norm}"), input)
            } else {
                ("final_norm".into(), "blocks.1".into())
            };
            let mut xs = values(&raw, &m.tensors[&format!("{}/pp/{source}", case.id)]);
            if index == 6 {
                xs = xs
                    .chunks_exact(5 * 64)
                    .flat_map(|row| row[4 * 64..].iter().copied())
                    .collect();
            }
            let rows = if index == 6 {
                case.batch * 3
            } else {
                case.batch * 15
            };
            assert_eq!(xs.len(), rows * 64);
            let x = Tensor::<2>::from_data(TensorData::new(xs, [rows, 64]), &device);
            let w = Tensor::<1>::from_data(
                TensorData::new(
                    values(&raw, &m.tensors[&format!("weight/{name}.weight")]),
                    [64],
                ),
                &device,
            );
            let b = Tensor::<1>::from_data(
                TensorData::new(
                    values(&raw, &m.tensors[&format!("weight/{name}.bias")]),
                    [64],
                ),
                &device,
            );
            let centered = x.clone() - mean(x.clone());
            let var = mean(centered.clone().square());
            let baseline = centered * (var + 1e-5).sqrt().recip() * w.clone().reshape([1, 64])
                + b.clone().reshape([1, 64]);
            let candidate = module::layer_norm(x, w, Some(b), 1e-5);
            for (kind, tensor) in [("baseline", baseline), ("candidate", candidate)] {
                let start = output.len();
                let v = tensor.to_data().to_vec::<f32>().unwrap();
                assert!(v.iter().all(|x| x.is_finite()));
                for x in v {
                    output.extend_from_slice(&x.to_le_bytes());
                }
                entries.insert(format!("{}/{kind}/{name}", case.id), json!({"shape":[rows,64],"offset_bytes":start,"length_bytes":output.len()-start}));
            }
        }
    }
    assert_eq!(entries.len(), 98);
    let p = Path::new(&a[3]);
    fs::create_dir(p).unwrap();
    write(&p.join("tensors.bin"), &output);
    let manifest = serde_json::to_vec(&json!({"schema":"banto.r1-native-norm.v1","tensors":entries,"fixture_manifest_sha256":a[2],"payload_sha256":sha256(&output)})).unwrap();
    write(&p.join("manifest.json"), &manifest);
    let files = [("tensors.bin", &output), ("manifest.json", &manifest)]
        .into_iter()
        .map(|(name, v)| json!({"name":name,"bytes":v.len(),"sha256":sha256(v)}))
        .collect::<Vec<_>>();
    write(
        &p.join("root-closed.json"),
        &serde_json::to_vec(&json!({"status":"complete","files":files})).unwrap(),
    );
    println!(
        "{}",
        json!({"same_input_candidate_calls":49,"baseline_calls":49,"full_forward":0,"training":false})
    );
}
