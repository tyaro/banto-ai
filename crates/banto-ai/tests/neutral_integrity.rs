use banto_ai::checkpoint::{NeutralModel, sha256};
use serde_json::Value;
use std::{env, fs, path::PathBuf};
fn reference() -> (Vec<u8>, Vec<u8>) {
    let root = PathBuf::from(
        env::var("BANTO_R1_REPO").expect("set BANTO_R1_REPO for pinned reference tests"),
    );
    let path = root.join("artifacts/care-learning-fold-0-20261016");
    (
        fs::read(path.join("selected-neutral-layout.json")).unwrap(),
        fs::read(path.join("selected-neutral.bin")).unwrap(),
    )
}
fn load(l: &[u8], b: &[u8]) -> bool {
    NeutralModel::from_reference(l, b, &sha256(l), &sha256(b)).is_ok()
}
#[test]
fn pinned_reference_and_corrupt_state_are_distinguished() {
    let (layout, raw) = reference();
    assert!(load(&layout, &raw));
    assert!(NeutralModel::from_reference(&layout, &raw, "incorrect", &sha256(&raw)).is_err());
    let mut value: Value = serde_json::from_slice(&layout).unwrap();
    value["tensors"][0]["shape"] = serde_json::json!([65]);
    assert!(!load(&serde_json::to_vec(&value).unwrap(), &raw));
    let mut duplicate: Value = serde_json::from_slice(&layout).unwrap();
    let entry = duplicate["tensors"][0].clone();
    duplicate["tensors"].as_array_mut().unwrap().push(entry);
    assert!(!load(&serde_json::to_vec(&duplicate).unwrap(), &raw));
    let mut overflow: Value = serde_json::from_slice(&layout).unwrap();
    overflow["tensors"][0]["offset_bytes"] = serde_json::json!(u64::MAX);
    assert!(!load(&serde_json::to_vec(&overflow).unwrap(), &raw));
    let mut nan = raw.clone();
    nan[..4].copy_from_slice(&f32::NAN.to_le_bytes());
    assert!(!load(&layout, &nan));
    let value: Value = serde_json::from_slice(&layout).unwrap();
    let mask = value["tensors"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["name"] == "model::time_mask")
        .unwrap();
    let mut noncausal = raw.clone();
    noncausal[mask["offset_bytes"].as_u64().unwrap() as usize + 1] = 1;
    assert!(!load(&layout, &noncausal));
    let mut tail = raw.clone();
    tail.push(0);
    assert!(!load(&layout, &tail));
}
