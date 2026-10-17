//! Fixed width128 CPU reference context normalization, expressed as tensor ops.
//! float64 std is independent of the float32 mean, as in ATen's CPU reduction.
//! Forward/graph participation and backward acceptance are separate gates.
use burn::tensor::{FloatDType, Tensor};

/// Return mean, raw population std, floored scale and normalized context.
/// The mean follows the four-vector/four-lane CPU sum order for width128.
/// All casts, slices and arithmetic remain in the autodiff graph.
pub fn reference_context(
    x: Tensor<3>,
    floor: Tensor<3>,
) -> (Tensor<3>, Tensor<3>, Tensor<3>, Tensor<3>) {
    let [batch, series, width] = x.dims();
    assert_eq!(width, 128);
    assert_eq!(series, 3);
    assert!(batch > 0);
    assert_eq!(floor.dims(), [1, series, 1]);
    let rows = batch * series;
    let blocks = x.clone().reshape([rows, 8, 4, 4]);
    let mut acc = blocks
        .clone()
        .slice([0..rows, 0..1, 0..4, 0..4])
        .zeros_like();
    for j in 0..8 {
        acc = acc + blocks.clone().slice([0..rows, j..j + 1, 0..4, 0..4]);
    }
    let acc = acc.reshape([rows, 4, 4]);
    let mut vector = acc.clone().slice([0..rows, 0..1, 0..4]);
    for k in 1..4 {
        vector = vector + acc.clone().slice([0..rows, k..k + 1, 0..4]);
    }
    let vector = vector.reshape([rows, 4]);
    let mut total = vector.clone().slice([0..rows, 0..1]).zeros_like();
    for lane in 0..4 {
        total = total + vector.clone().slice([0..rows, lane..lane + 1]);
    }
    let mean = ((total + 0.0) / 128.0).reshape([batch, series, 1]);

    // ATen std_cpu uses a serial WelfordData<double> for each 128-value row.
    // A float32 cast happens after the float64 population sqrt, not before it.
    let wide = x.clone().reshape([rows, width]).cast(FloatDType::F64);
    let mut running_mean = wide.clone().slice([0..rows, 0..1]).zeros_like();
    let mut m2 = running_mean.zeros_like();
    for j in 0..width {
        let value = wide.clone().slice([0..rows, j..j + 1]);
        let delta = value.clone() - running_mean.clone();
        running_mean = running_mean + delta.clone() / (j + 1) as f64;
        m2 = m2 + delta * (value - running_mean.clone());
    }
    let std = (m2 / width as f64)
        .sqrt()
        .cast(FloatDType::F32)
        .reshape([batch, series, 1]);
    let scale = std.clone().max_pair(floor);
    let normalized = (x - mean.clone()) / scale.clone();
    (mean, std, scale, normalized)
}
