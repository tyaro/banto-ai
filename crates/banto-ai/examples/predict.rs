//! Fixed-fixture parity entry point; never loads future targets or runs training.
use banto_ai::{
    Error, ForecastInput, Result, SmallForecaster,
    checkpoint::{NeutralModel, sha256},
};
use serde::Deserialize;
use serde_json::json;
use std::{collections::BTreeSet, env, fs, path::Path};
#[derive(Deserialize)]
struct Fixtures {
    schema: String,
    inputs_sha256: String,
    model_layout_sha256: String,
    model_payload_sha256: String,
    cases: Vec<Case>,
}
#[derive(Deserialize)]
struct Case {
    id: String,
    batch: usize,
    offset_bytes: usize,
    length_bytes: usize,
}
fn write_new(path: &Path, raw: &[u8]) -> Result<()> {
    use std::io::Write;
    if raw.len() > 32 * 1024 * 1024 {
        return Err(Error::Model("output size cap".into()));
    }
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    file.write_all(raw)?;
    Ok(())
}
fn bounded_read(path: &str, limit: u64) -> Result<Vec<u8>> {
    if fs::metadata(path)?.len() > limit {
        return Err(Error::Input("input file size cap".into()));
    }
    Ok(fs::read(path)?)
}
fn execute(args: &[String], out: &Path) -> Result<()> {
    let layout = bounded_read(&args[0], 256 * 1024)?;
    let payload = bounded_read(&args[1], 32 * 1024 * 1024)?;
    let manifest = bounded_read(&args[2], 256 * 1024)?;
    let inputs = bounded_read(&args[3], 32 * 1024 * 1024)?;
    let fixtures: Fixtures = serde_json::from_slice(&manifest)?;
    if fixtures.schema != "banto.r1-forward-fixtures.v1"
        || fixtures.cases.len() > 16
        || sha256(&inputs) != fixtures.inputs_sha256
    {
        return Err(Error::Integrity("fixture schema/count/input digest".into()));
    }
    let model = SmallForecaster::from_neutral(NeutralModel::from_reference(
        &layout,
        &payload,
        &fixtures.model_layout_sha256,
        &fixtures.model_payload_sha256,
    )?);
    let mut raw = Vec::new();
    let mut index = Vec::new();
    let mut seen = BTreeSet::new();
    let mut end = 0;
    for case in fixtures.cases {
        let next = case
            .offset_bytes
            .checked_add(case.length_bytes)
            .ok_or_else(|| Error::Input("case overflow".into()))?;
        if !seen.insert(case.id.clone())
            || case.offset_bytes != end
            || next > inputs.len()
            || case.length_bytes % 4 != 0
            || !(1..=8).contains(&case.batch)
            || case.length_bytes != case.batch * 384 * 4
        {
            return Err(Error::Input("fixture case layout/identity/shape".into()));
        }
        let values = inputs[end..next]
            .chunks_exact(4)
            .map(|b| f32::from_le_bytes(b.try_into().unwrap()))
            .collect();
        end = next;
        let (forecast, traces) = model.predict_traced(&ForecastInput::new(case.batch, values)?)?;
        if forecast.quantiles.len() != case.batch * 288 {
            return Err(Error::Backend("forecast shape".into()));
        }
        let mut entries = Vec::new();
        for t in traces {
            let start = raw.len();
            for v in t.values {
                raw.extend_from_slice(&v.to_le_bytes());
            }
            entries.push(json!({"name":t.name,"shape":t.shape,"offset_bytes":start,"length_bytes":raw.len()-start}));
        }
        index.push(json!({"id":case.id,"batch":case.batch,"traces":entries}));
    }
    if end != inputs.len() {
        return Err(Error::Input("unlisted fixture bytes".into()));
    }
    write_new(&out.join("rust-traces.bin"), &raw)?;
    write_new(
        &out.join("traces-layout.json"),
        &serde_json::to_vec(
            &json!({"schema":"banto.r1-rust-traces.v1","cases":index,"payload_sha256":sha256(&raw)}),
        )?,
    )?;
    write_new(
        &out.join("summary.json"),
        &serde_json::to_vec(
            &json!({"status":"complete","cases":index.len(),"backend":"Burn0.22 Flex CPU","training":false,"test_or_truth":false}),
        )?,
    )?;
    Ok(())
}
fn main() -> std::result::Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 5 {
        return Err("usage: predict LAYOUT MODEL FIXTURES INPUTS NEW_OUTPUT_DIR".into());
    }
    let out = Path::new(&args[4]);
    fs::create_dir(out)?;
    let result = execute(&args, out);
    let mut files = Vec::new();
    for entry in fs::read_dir(out)? {
        let p = entry?.path();
        let raw = fs::read(&p)?;
        files.push(json!({"name":p.file_name().unwrap().to_string_lossy(),"bytes":raw.len(),"sha256":sha256(&raw)}));
    }
    let status = if result.is_ok() { "complete" } else { "failed" };
    let error = result.as_ref().err().map(|e| e.to_string());
    write_new(
        &out.join("root-closed.json"),
        &serde_json::to_vec(&json!({"status":status,"files":files,"failure":error}))?,
    )?;
    result?;
    println!("{}", json!({"status":"complete","output":out}));
    Ok(())
}
