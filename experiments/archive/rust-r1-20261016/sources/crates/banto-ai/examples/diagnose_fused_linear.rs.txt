//! Candidate-only evaluation on all 154 closed Python-path linear inputs.
use banto_ai::{checkpoint::sha256, fused_linear::finite_fused_linear};
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
struct Data {
    m: Manifest,
    raw: Vec<u8>,
    device: Device,
}
impl Data {
    fn values(&self, key: &str) -> Vec<f32> {
        let e = &self.m.tensors[key];
        assert_eq!(e.length_bytes, e.shape.iter().product::<usize>() * 4);
        let end = e.offset_bytes.checked_add(e.length_bytes).unwrap();
        assert!(end <= self.raw.len());
        self.raw[e.offset_bytes..end]
            .chunks_exact(4)
            .map(|v| f32::from_le_bytes(v.try_into().unwrap()))
            .collect()
    }
    fn flat(&self, key: &str, k: usize) -> Tensor<2> {
        let v = self.values(key);
        assert_eq!(v.len() % k, 0);
        let rows = v.len() / k;
        Tensor::from_data(TensorData::new(v, [rows, k]), &self.device)
    }
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
    assert_eq!(m.schema, "banto.r1-all-layer-audit.v1");
    assert_eq!(m.cases.len(), 7);
    let raw = fs::read(&a[1]).unwrap();
    assert_eq!(sha256(&raw), m.payload_sha256);
    let d = Data {
        m,
        raw,
        device: Device::flex(),
    };
    let mut output = Vec::new();
    let mut entries = BTreeMap::new();
    for c in &d.m.cases {
        let mut modules = vec![("patch".to_string(), "normalized_context".to_string(), false)];
        for block in 0..2 {
            for (kind, norm) in [("temporal", 0), ("variate", 1)] {
                for layer in ["q", "k", "v"] {
                    modules.push((
                        format!("blocks.{block}.{kind}.{layer}"),
                        format!("blocks.{block}.norms.{norm}"),
                        kind == "variate",
                    ));
                }
                modules.push((
                    format!("blocks.{block}.{kind}"),
                    format!("blocks.{block}.{kind}.mixed"),
                    false,
                ));
            }
            modules.push((
                format!("blocks.{block}.ff.0"),
                format!("blocks.{block}.norms.2"),
                false,
            ));
            modules.push((
                format!("blocks.{block}.ff.2"),
                format!("blocks.{block}.ff.1"),
                false,
            ));
        }
        modules.push(("head".into(), "final_norm".into(), false));
        assert_eq!(modules.len(), 22);
        for (node, source, transpose) in modules {
            let weight_name = if node.ends_with("temporal") || node.ends_with("variate") {
                format!("{node}.out")
            } else {
                node.clone()
            };
            let key = format!("weight/{weight_name}.weight");
            let shape = &d.m.tensors[&key].shape;
            assert_eq!(shape.len(), 2);
            let (n, k) = (shape[0], shape[1]);
            let mut x = d.flat(&format!("{}/pp/{source}", c.id), k);
            if transpose {
                x = x
                    .reshape([c.batch, 3, 5, 64])
                    .swap_dims(1, 2)
                    .reshape([c.batch * 15, 64]);
            }
            let w = Tensor::<2>::from_data(TensorData::new(d.values(&key), [n, k]), &d.device)
                .transpose();
            let b = Tensor::<1>::from_data(
                TensorData::new(d.values(&format!("weight/{weight_name}.bias")), [n]),
                &d.device,
            );
            let y = finite_fused_linear(x, w, b).unwrap();
            let values = y.to_data().to_vec::<f32>().unwrap();
            assert!(values.iter().all(|v| v.is_finite()));
            let expected_shape = &d.m.tensors[&format!("{}/pp/{node}", c.id)].shape;
            assert_eq!(values.len(), expected_shape.iter().product::<usize>());
            let start = output.len();
            for v in values {
                output.extend_from_slice(&v.to_le_bytes());
            }
            entries.insert(format!("{}/candidate/{node}",c.id),json!({"shape":expected_shape,"offset_bytes":start,"length_bytes":output.len()-start}));
        }
    }
    assert_eq!(entries.len(), 154);
    let p = Path::new(&a[3]);
    fs::create_dir(p).unwrap();
    write(&p.join("tensors.bin"), &output);
    let manifest=serde_json::to_vec(&json!({"schema":"banto.r1-fused-linear-local.v1","tensors":entries,"fixture_manifest_sha256":a[2],"payload_sha256":sha256(&output)})).unwrap();
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
        json!({"candidate_linear_calls":154,"old_baseline_calls":0,"full_forward":0,"training":false})
    );
}
