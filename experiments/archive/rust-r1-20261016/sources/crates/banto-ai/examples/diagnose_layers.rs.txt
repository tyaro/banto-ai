//! Fixed 55-node audit: current Rust path and isolated reference-input kernels.
use banto_ai::checkpoint::sha256;
use burn::tensor::{Bool, Device, Tensor, TensorData, activation};
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
    nodes: Vec<String>,
    anchors: Vec<String>,
}
#[derive(Deserialize)]
struct Manifest {
    schema: String,
    payload_sha256: String,
    cases: Vec<Case>,
    tensors: BTreeMap<String, Entry>,
}
struct Data {
    m: Manifest,
    raw: Vec<u8>,
    device: Device,
}
impl Data {
    fn values(&self, key: &str) -> Vec<f32> {
        let e = &self.m.tensors[key];
        let end = e.offset_bytes.checked_add(e.length_bytes).unwrap();
        assert!(end <= self.raw.len());
        self.raw[e.offset_bytes..end]
            .chunks_exact(4)
            .map(|v| f32::from_le_bytes(v.try_into().unwrap()))
            .collect()
    }
    fn p<const D: usize>(&self, key: &str, shape: [usize; D]) -> Tensor<D> {
        assert_eq!(
            self.m.tensors[key].shape.iter().product::<usize>(),
            shape.iter().product::<usize>()
        );
        Tensor::from_data(TensorData::new(self.values(key), shape), &self.device)
    }
    fn w<const D: usize>(&self, key: &str, shape: [usize; D]) -> Tensor<D> {
        self.p(&format!("weight/{key}"), shape)
    }
    fn linear<const D: usize>(&self, x: Tensor<D>, key: &str, out: usize) -> Tensor<D> {
        let mut shape = x.dims();
        let width = shape[D - 1];
        let rows = shape.iter().product::<usize>() / width;
        let w = self.w(&format!("{key}.weight"), [out, width]).transpose();
        let bias = self.w(&format!("{key}.bias"), [1, out]);
        shape[D - 1] = out;
        (x.reshape([rows, width]).matmul(w) + bias).reshape(shape)
    }
    fn norm<const D: usize>(&self, x: Tensor<D>, key: &str) -> Tensor<D> {
        let mu = mean(x.clone());
        let centered = x - mu;
        let var = mean(centered.clone().square());
        let mut shape = [1; D];
        shape[D - 1] = 64;
        centered * (var + 1e-5).sqrt().recip() * self.w(&format!("{key}.weight"), shape)
            + self.w(&format!("{key}.bias"), shape)
    }
    fn scale(&self, x: Tensor<3>) -> Tensor<3> {
        let mu = mean(x.clone());
        mean((x - mu).square())
            .sqrt()
            .max_pair(self.w("scale_floor", [1, 3, 1]))
    }
}
fn mean<const D: usize>(x: Tensor<D>) -> Tensor<D> {
    let mut shape = x.dims();
    let width = shape[D - 1];
    assert!(width.is_power_of_two());
    let rows = shape.iter().product::<usize>() / width;
    let mut count = width;
    let mut x = x.reshape([rows, width]);
    while count > 1 {
        x = x
            .reshape([rows, count / 2, 2])
            .sum_dim(2)
            .reshape([rows, count / 2]);
        count /= 2;
    }
    shape[D - 1] = 1;
    (x / width as f32).reshape(shape)
}
fn gelu<const D: usize>(x: Tensor<D>) -> Tensor<D> {
    x.clone() * 0.5 * ((x / std::f32::consts::SQRT_2).erf() + 1.)
}
fn softplus<const D: usize>(x: Tensor<D>) -> Tensor<D> {
    let high = x.clone().greater_elem(20.);
    x.clone().clamp_max(20.).exp().log1p().mask_where(high, x)
}
fn ordered(head: Tensor<3>, b: usize) -> Tensor<4> {
    let raw = head.reshape([b, 3, 32, 3]);
    let m: Tensor<3> = raw.clone().slice([0..b, 0..3, 0..32, 0..1]).squeeze_dim(3);
    let l: Tensor<3> = raw.clone().slice([0..b, 0..3, 0..32, 1..2]).squeeze_dim(3);
    let h: Tensor<3> = raw.slice([0..b, 0..3, 0..32, 2..3]).squeeze_dim(3);
    Tensor::stack(vec![m.clone() - softplus(l), m.clone(), m + softplus(h)], 3)
}
struct Output {
    raw: Vec<u8>,
    entries: BTreeMap<String, serde_json::Value>,
    certs: Vec<serde_json::Value>,
}
struct Audit<'a> {
    data: &'a Data,
    case: &'a Case,
    out: &'a mut Output,
    seen: Vec<String>,
}
impl Audit<'_> {
    fn pp<const D: usize>(&self, key: &str, shape: [usize; D]) -> Tensor<D> {
        self.data.p(&format!("{}/pp/{key}", self.case.id), shape)
    }
    fn node<const D: usize>(&mut self, key: &str, rr: Tensor<D>, rp: Tensor<D>) -> Tensor<D> {
        assert_eq!(self.case.nodes[self.seen.len()], key);
        self.seen.push(key.to_string());
        for (branch, t) in [("rr", &rr), ("rp", &rp)] {
            let v = t.to_data().to_vec::<f32>().unwrap();
            let shape = t.dims();
            assert!(v.iter().all(|x|x.is_finite() || (key.ends_with(".logits") && *x==f32::NEG_INFINITY)));
            if branch == "rr" && self.case.anchors.iter().any(|n| n == key) {
                let anchor = self.data.values(&format!("{}/anchor/{key}", self.case.id));
                assert_eq!(v.len(), anchor.len());
                assert!(
                    v.iter()
                        .zip(&anchor)
                        .all(|(a, b)| a.to_bits() == b.to_bits()),
                    "own-path anchor differs: {} {}",
                    self.case.id,
                    key
                );
                self.out
                    .certs
                    .push(json!({"case":self.case.id,"node":key,"byte_exact":true}));
            }
            let start = self.out.raw.len();
            for x in v {
                self.out.raw.extend_from_slice(&x.to_le_bytes());
            }
            self.out.entries.insert(format!("{}/{branch}/{key}",self.case.id),json!({"shape":shape.to_vec(),"offset_bytes":start,"length_bytes":self.out.raw.len()-start}));
        }
        rr
    }
    fn attention(&mut self, x: Tensor<3>, px: Tensor<3>, key: &str, causal: bool) -> Tensor<3> {
        let [batch, n, _] = x.dims();
        let mut proj = Vec::new();
        for layer in ["q", "k", "v"] {
            let name = format!("{key}.{layer}");
            let rr = self.data.linear(x.clone(), &name, 64);
            let rp = self.data.linear(px.clone(), &name, 64);
            proj.push(self.node(&name, rr, rp));
        }
        let heads = |x: Tensor<3>| x.reshape([batch, n, 4, 16]).swap_dims(1, 2);
        let q = heads(proj[0].clone());
        let k = heads(proj[1].clone());
        let v = heads(proj[2].clone());
        let pq = heads(self.pp(&format!("{key}.q"), [batch, n, 64]));
        let pk = heads(self.pp(&format!("{key}.k"), [batch, n, 64]));
        let pv = heads(self.pp(&format!("{key}.v"), [batch, n, 64]));
        let mut logits = q.matmul(k.swap_dims(2, 3)) / 4.;
        let mut plogits = pq.matmul(pk.swap_dims(2, 3)) / 4.;
        if causal {
            let mask: Vec<bool> = (0..n * n).map(|i| i % n > i / n).collect();
            let mask = Tensor::<4, Bool>::from_data(
                TensorData::new(mask, [1, 1, n, n]),
                &self.data.device,
            );
            logits = logits.mask_fill(mask.clone(), f32::NEG_INFINITY);
            plogits = plogits.mask_fill(mask, f32::NEG_INFINITY);
        }
        let logits = self.node(&format!("{key}.logits"), logits, plogits);
        let probs = activation::softmax(logits, 3);
        let pprobs = activation::softmax(self.pp(&format!("{key}.logits"), [batch, 4, n, n]), 3);
        let probs = self.node(&format!("{key}.probs"), probs, pprobs);
        let mixed = probs.matmul(v).swap_dims(1, 2).reshape([batch, n, 64]);
        let pmixed = self
            .pp(&format!("{key}.probs"), [batch, 4, n, n])
            .matmul(pv)
            .swap_dims(1, 2)
            .reshape([batch, n, 64]);
        let mixed = self.node(&format!("{key}.mixed"), mixed, pmixed);
        let rr = self.data.linear(mixed, &format!("{key}.out"), 64);
        let rp = self.data.linear(
            self.pp(&format!("{key}.mixed"), [batch, n, 64]),
            &format!("{key}.out"),
            64,
        );
        self.node(key, rr, rp)
    }
}
impl Audit<'_> {
    fn run(&mut self) {
        let b = self.case.batch;
        let x = self.data.p(&format!("{}/input", self.case.id), [b, 3, 128]);
        let mu = self.node("context_center", mean(x.clone()), mean(x.clone()));
        let scale = self.node(
            "context_scale",
            self.data.scale(x.clone()),
            self.data.scale(x.clone()),
        );
        let normalized = (x.clone() - mu.clone()) / scale.clone();
        let pnormalized =
            (x - self.pp("context_center", [b, 3, 1])) / self.pp("context_scale", [b, 3, 1]);
        let normalized = self.node("normalized_context", normalized, pnormalized);
        let patch = self
            .data
            .linear(normalized.reshape([b, 3, 4, 32]), "patch", 64);
        let ppatch = self.data.linear(
            self.pp("normalized_context", [b, 3, 128])
                .reshape([b, 3, 4, 32]),
            "patch",
            64,
        );
        let patch = self.node("patch", patch, ppatch);
        let query = self.data.w("horizon", [1, 1, 1, 64]).expand([b, 3, 1, 64]);
        let position = self.data.w("position", [1, 1, 5, 64]);
        let tokens = Tensor::cat(vec![patch, query.clone()], 2) + position.clone();
        let ptokens = Tensor::cat(vec![self.pp("patch", [b, 3, 4, 64]), query], 2) + position;
        let mut tokens = self.node("tokens", tokens, ptokens);
        for i in 0..2 {
            let key = format!("blocks.{i}");
            let before = if i == 0 {
                "tokens".to_string()
            } else {
                format!("blocks.{}", i - 1)
            };
            let z = self.data.norm(tokens.clone(), &format!("{key}.norms.0"));
            let pz = self
                .data
                .norm(self.pp(&before, [b, 3, 5, 64]), &format!("{key}.norms.0"));
            let z = self.node(&format!("{key}.norms.0"), z, pz);
            let t = self.attention(
                z.reshape([b * 3, 5, 64]),
                self.pp(&format!("{key}.norms.0"), [b * 3, 5, 64]),
                &format!("{key}.temporal"),
                true,
            );
            let pr = self.pp(&before, [b, 3, 5, 64])
                + self
                    .pp(&format!("{key}.temporal"), [b * 3, 5, 64])
                    .reshape([b, 3, 5, 64]);
            tokens = self.node(
                &format!("{key}.residual0"),
                tokens + t.reshape([b, 3, 5, 64]),
                pr,
            );
            let z = self.data.norm(tokens.clone(), &format!("{key}.norms.1"));
            let pz = self.data.norm(
                self.pp(&format!("{key}.residual0"), [b, 3, 5, 64]),
                &format!("{key}.norms.1"),
            );
            let z = self.node(&format!("{key}.norms.1"), z, pz);
            let v = self.attention(
                z.swap_dims(1, 2).reshape([b * 5, 3, 64]),
                self.pp(&format!("{key}.norms.1"), [b, 3, 5, 64])
                    .swap_dims(1, 2)
                    .reshape([b * 5, 3, 64]),
                &format!("{key}.variate"),
                false,
            );
            let pr = self.pp(&format!("{key}.residual0"), [b, 3, 5, 64])
                + self
                    .pp(&format!("{key}.variate"), [b * 5, 3, 64])
                    .reshape([b, 5, 3, 64])
                    .swap_dims(1, 2);
            tokens = self.node(
                &format!("{key}.residual1"),
                tokens + v.reshape([b, 5, 3, 64]).swap_dims(1, 2),
                pr,
            );
            let z = self.data.norm(tokens.clone(), &format!("{key}.norms.2"));
            let pz = self.data.norm(
                self.pp(&format!("{key}.residual1"), [b, 3, 5, 64]),
                &format!("{key}.norms.2"),
            );
            let z = self.node(&format!("{key}.norms.2"), z, pz);
            let h = self.data.linear(z, &format!("{key}.ff.0"), 128);
            let ph = self.data.linear(
                self.pp(&format!("{key}.norms.2"), [b, 3, 5, 64]),
                &format!("{key}.ff.0"),
                128,
            );
            let h = self.node(&format!("{key}.ff.0"), h, ph);
            let h = self.node(
                &format!("{key}.ff.1"),
                gelu(h),
                gelu(self.pp(&format!("{key}.ff.0"), [b, 3, 5, 128])),
            );
            let ff = self.data.linear(h, &format!("{key}.ff.2"), 64);
            let pff = self.data.linear(
                self.pp(&format!("{key}.ff.1"), [b, 3, 5, 128]),
                &format!("{key}.ff.2"),
                64,
            );
            let ff = self.node(&format!("{key}.ff.2"), ff, pff);
            let pr = self.pp(&format!("{key}.residual1"), [b, 3, 5, 64])
                + self.pp(&format!("{key}.ff.2"), [b, 3, 5, 64]);
            tokens = self.node(&key, tokens + ff, pr);
        }
        let last = tokens.slice([0..b, 0..3, 4..5, 0..64]).reshape([b, 3, 64]);
        let plast = self
            .pp("blocks.1", [b, 3, 5, 64])
            .slice([0..b, 0..3, 4..5, 0..64])
            .reshape([b, 3, 64]);
        let last = self.node(
            "final_norm",
            self.data.norm(last, "final_norm"),
            self.data.norm(plast, "final_norm"),
        );
        let head = self.node(
            "head",
            self.data.linear(last, "head", 96),
            self.data
                .linear(self.pp("final_norm", [b, 3, 64]), "head", 96),
        );
        let q = self.node(
            "normalized_quantiles",
            ordered(head, b),
            ordered(self.pp("head", [b, 3, 96]), b),
        );
        let physical = q * scale.reshape([b, 3, 1, 1]) + mu.reshape([b, 3, 1, 1]);
        let pphysical = self.pp("normalized_quantiles", [b, 3, 32, 3])
            * self.pp("context_scale", [b, 3, 1]).reshape([b, 3, 1, 1])
            + self.pp("context_center", [b, 3, 1]).reshape([b, 3, 1, 1]);
        self.node("quantiles", physical, pphysical);
        assert_eq!(self.seen, self.case.nodes);
    }
}
fn write(p: &Path, raw: &[u8]) {
    assert!(raw.len() < 32 * 1024 * 1024);
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
    assert!(
        fs::metadata(&a[0]).unwrap().len() < 256 * 1024
            && fs::metadata(&a[1]).unwrap().len() < 32 * 1024 * 1024
    );
    let m = fs::read(&a[0]).unwrap();
    assert_eq!(sha256(&m), a[2]);
    let m: Manifest = serde_json::from_slice(&m).unwrap();
    assert_eq!(m.schema, "banto.r1-all-layer-audit.v1");
    assert_eq!(m.cases.len(), 7);
    let raw = fs::read(&a[1]).unwrap();
    assert_eq!(sha256(&raw), m.payload_sha256);
    let data = Data {
        m,
        raw,
        device: Device::flex(),
    };
    let mut out = Output {
        raw: vec![],
        entries: BTreeMap::new(),
        certs: vec![],
    };
    for case in &data.m.cases {
        assert_eq!(case.nodes.len(), 55);
        let mut audit = Audit {
            data: &data,
            case,
            out: &mut out,
            seen: vec![],
        };
        audit.run();
    }
    assert_eq!(out.entries.len(), 770);
    assert_eq!(out.certs.len(), 161);
    let p = Path::new(&a[3]);
    fs::create_dir(p).unwrap();
    write(&p.join("tensors.bin"), &out.raw);
    let manifest=serde_json::to_vec(&json!({"tensors":out.entries,"fixture_manifest_sha256":a[2],"payload_sha256":sha256(&out.raw)})).unwrap();
    write(&p.join("manifest.json"), &manifest);
    let cert = serde_json::to_vec(&out.certs).unwrap();
    write(&p.join("anchor-certificates.json"), &cert);
    let summary=serde_json::to_vec(&json!({"cases":7,"nodes_per_case":55,"isolated_node_evaluations":385,"rust_diagnostic_replays":7,"saved_anchors_byte_exact":161,"core_modified":false,"training":false})).unwrap();
    write(&p.join("summary.json"), &summary);
    let files = [
        ("tensors.bin", &out.raw),
        ("manifest.json", &manifest),
        ("anchor-certificates.json", &cert),
        ("summary.json", &summary),
    ]
    .into_iter()
    .map(|(name, v)| json!({"name":name,"bytes":v.len(),"sha256":sha256(v)}))
    .collect::<Vec<_>>();
    write(
        &p.join("root-closed.json"),
        &serde_json::to_vec(&json!({"status":"complete","files":files})).unwrap(),
    );
    println!(
        "{}",
        json!({"status":"complete","nodes":385,"anchors_exact":161})
    );
}
