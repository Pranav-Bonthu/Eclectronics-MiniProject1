<#
.SYNOPSIS
    Regenerate every display asset in images/ and docs/ from the design files.

.DESCRIPTION
    Nothing in images/ is hand-made -- this script rebuilds all of it from
    kicad/ and ltspice/. Run it after changing the schematic, the board, or the
    simulation so the README never drifts from the design.

    The Monte Carlo waveform figure additionally needs LTspice's exported .txt,
    which is ~11 MB and not committed. Point -Waveforms at it, or let that one
    figure be skipped.

.EXAMPLE
    pwsh tools/generate_assets.ps1
#>
param(
    [string]$KicadCli = "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    [string]$Waveforms = "$env:USERPROFILE\OneDrive - Olin College of Engineering\Documents\LTspice\eclectronicsmp12.txt"
)

$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent $PSScriptRoot
$board = Join-Path $root "kicad\eclectronicsmp1.kicad_pcb"
$sch   = Join-Path $root "kicad\eclectronicsmp1.kicad_sch"
$img   = Join-Path $root "images"
$tmp   = Join-Path $root ".tmp"

if (-not (Test-Path $KicadCli)) { throw "kicad-cli not found at $KicadCli" }
New-Item -ItemType Directory -Force -Path $img, $tmp | Out-Null

Write-Host "==> KiCad schematic (PDF + PNG)"
& $KicadCli sch export pdf -o (Join-Path $root "docs\kicad-schematic.pdf") $sch | Out-Null
python (Join-Path $PSScriptRoot "pdf_to_png.py") `
    (Join-Path $root "docs\kicad-schematic.pdf") (Join-Path $img "kicad-schematic.png") 300

Write-Host "==> PCB 3D renders"
& $KicadCli pcb render --side top    --zoom 1.35 --quality high --width 2000 --height 1180 `
    --background opaque -o (Join-Path $img "pcb-3d-top.png") $board | Out-Null
& $KicadCli pcb render --side bottom --zoom 1.35 --quality high --width 2000 --height 1180 `
    --background opaque -o (Join-Path $img "pcb-3d-bottom.png") $board | Out-Null
& $KicadCli pcb render --rotate '-30,0,30' --perspective --floor --zoom 1.5 --quality high `
    --width 2000 --height 1300 --background opaque -o (Join-Path $img "pcb-3d-iso.png") $board | Out-Null

python (Join-Path $PSScriptRoot "trim_render.py") `
    (Join-Path $img "pcb-3d-top.png") (Join-Path $img "pcb-3d-bottom.png") `
    (Join-Path $img "pcb-3d-iso.png")

Write-Host "==> PCB 2D layer views"
python (Join-Path $PSScriptRoot "render_pcb_layers.py")

Write-Host "==> LTspice schematic"
python (Join-Path $PSScriptRoot "render_ltspice_asc.py")

Write-Host "==> Monte Carlo figures"
python (Join-Path $PSScriptRoot "plot_montecarlo.py") --waveforms $Waveforms

Write-Host "==> Gerber package"
$gerbers = Join-Path $root "fabrication\gerbers"
& $KicadCli pcb export gerbers -o $gerbers $board | Out-Null
Compress-Archive -Path (Join-Path $gerbers "*") `
    -DestinationPath (Join-Path $root "fabrication\eclectronicsmp1-gerbers.zip") -Force

Write-Host "==> Design rule checks"
& $KicadCli pcb drc --format report -o (Join-Path $tmp "drc.rpt") $board
& $KicadCli sch erc --format report -o (Join-Path $tmp "erc.rpt") $sch

Write-Host "`nDone. Assets written to images/, docs/ and fabrication/." -ForegroundColor Green
