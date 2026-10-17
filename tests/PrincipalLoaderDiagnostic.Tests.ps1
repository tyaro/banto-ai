$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot '../tools/windows_principal_loader_diagnostic.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count -ne 0) { throw 'Launcher parse failed.' }
foreach ($name in @('Read-PrincipalDiagnosticBytes', 'New-PrincipalLoaderDiagnosticCommand', 'Write-PrincipalDiagnosticJson')) {
    $found = @($ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $false))
    if ($found.Count -ne 1) { throw 'Expected one pure function.' }
    . ([scriptblock]::Create($found[0].Extent.Text))
}
foreach ($length in @(0, 262145)) {
    $stream = [IO.MemoryStream]::new([byte[]]::new($length))
    $rejected = $false
    try { $null = Read-PrincipalDiagnosticBytes -Stream $stream } catch { $rejected = $true } finally { $stream.Dispose() }
    if (-not $rejected) { throw 'Invalid stream bound accepted.' }
}
$stream = [IO.MemoryStream]::new([byte[]]@(1, 2, 3))
try { $actual = Read-PrincipalDiagnosticBytes -Stream $stream } finally { $stream.Dispose() }
if ($actual -isnot [byte[]] -or ($actual -join ',') -ne '1,2,3') { throw 'Exact bytes changed.' }
$rejected = $false
try { $null = New-PrincipalLoaderDiagnosticCommand -Bytes $actual } catch { $rejected = $true }
if (-not $rejected) { throw 'Wrong assembly hash accepted.' }
$library = Join-Path $PSScriptRoot '../artifacts/principal-setup-b-2026-09-15/PrincipalSetup-build-01.dll'
$stream = [IO.File]::OpenRead($library)
try { $bytes = Read-PrincipalDiagnosticBytes -Stream $stream } finally { $stream.Dispose() }
$arguments = New-PrincipalLoaderDiagnosticCommand -Bytes $bytes
$prefix = '-NoProfile -NonInteractive -Command "& { '
if (-not $arguments.StartsWith($prefix) -or -not $arguments.EndsWith(' }"') -or $arguments.Length -gt 29041) { throw 'Command framing invalid.' }
$body = $arguments.Substring($prefix.Length, $arguments.Length - $prefix.Length - 3)
$bodyAst = [Management.Automation.Language.Parser]::ParseInput($body, [ref]$tokens, [ref]$errors)
if ($errors.Count -ne 0 -or $body.Contains('[Banto.') -or $body.Contains('Entry') -or $body.Contains('__HASH__') -or $body.Contains('__DATA__')) { throw 'Loader invokes preparation or has unresolved content.' }
$loads = @($bodyAst.FindAll({ param($node) $node -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $node.Expression.Extent.Text -eq '[Reflection.Assembly]' -and $node.Member.Value -eq 'Load' }, $true))
if ($loads.Count -ne 1 -or $loads[0].Arguments[0].Extent.Text -ne '$bytes') { throw 'Expected exactly one same-bytes assembly load.' }
$match = [regex]::Match($body, "FromBase64String\('([A-Za-z0-9+/=]+)'\)")
if (-not $match.Success) { throw 'Missing inline data.' }
$packed = [IO.MemoryStream]::new([Convert]::FromBase64String($match.Groups[1].Value), $false)
$decoder = [IO.Compression.DeflateStream]::new($packed, [IO.Compression.CompressionMode]::Decompress)
$output = [IO.MemoryStream]::new()
try { $decoder.CopyTo($output); $roundtrip = $output.ToArray() } finally { $decoder.Dispose(); $packed.Dispose(); $output.Dispose() }
if ([Convert]::ToBase64String($bytes) -cne [Convert]::ToBase64String($roundtrip)) { throw 'Inline bytes differ.' }
$guard = Join-Path ([IO.Path]::GetTempPath()) ('banto-loader-guard-' + [Guid]::NewGuid().ToString('N') + '.json')
try {
    Write-PrincipalDiagnosticJson -Path $guard -Value @{ attempt = 1 }
    $before = [IO.File]::ReadAllText($guard)
    $rejected = $false
    try { Write-PrincipalDiagnosticJson -Path $guard -Value @{ attempt = 2 } } catch [IO.IOException] { $rejected = $true }
    if (-not $rejected -or [IO.File]::ReadAllText($guard) -cne $before) { throw 'Attempt guard overwritten.' }
} finally { if ([IO.File]::Exists($guard)) { [IO.File]::Delete($guard) } }
[Console]::WriteLine('RESULT 8 loader diagnostic cases passed; no assembly load, child, UAC or preparation entry')
