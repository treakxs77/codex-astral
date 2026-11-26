param([string]$SourceDirectory,[string]$BuildDirectory,[string]$PayloadDirectory)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$build = $BuildDirectory
$source = $SourceDirectory
$archive = Join-Path $taskRoot 'Tests'
Copy-Item -LiteralPath (Join-Path $archive 'repo.json') -Destination $build -Force
$packs = $PayloadDirectory
Copy-Item -LiteralPath (Join-Path $taskRoot 'Tests\TestsFrench.cs') -Destination $build -Force
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$compiler = & $vswhere -latest -products '*' -find 'MSBuild\**\Bin\Roslyn\csc.exe' | Select-Object -First 1
Copy-Item -LiteralPath (Join-Path $archive 'TestsCompletion.cs') -Destination $build -Force
Copy-Item -LiteralPath (Join-Path $archive 'definitions-test.txt') -Destination $build -Force
$policyExe = Join-Path $build 'TestsCompletion.exe'
& $compiler /nologo /target:exe /codepage:65001 ('/out:'+$policyExe) (Join-Path $build 'TestsCompletion.cs') (Join-Path $source 'Utility\CompletionPolicy.cs')
if ($LASTEXITCODE -ne 0) { throw 'Compilation tests règles impossible.' }
& $policyExe (Join-Path $build 'definitions-test.txt')
if ($LASTEXITCODE -ne 0) { throw 'Échec tests des règles Terminés.' }
$common = @('/nologo','/target:exe','/platform:x64','/codepage:65001','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll','/r:System.Xml.Linq.dll','/r:System.Windows.Forms.dll')
$common += '/r:'+(Join-Path $build 'Pathing.dll')
$common += @(Get-ChildItem -LiteralPath (Join-Path $build 'references') -File | Where-Object { $_.Extension -eq '.dll' -or $_.Name -eq 'Blish HUD.exe' } | ForEach-Object { '/r:'+$_.FullName })
$facade = Get-ChildItem -Path 'C:\Program Files*\Microsoft Visual Studio\*\*\Common7\IDE\Remote Debugger\x64\netstandard.dll' | Select-Object -First 1
$common += '/r:'+$facade.FullName
$frenchExe = Join-Path $build 'TestsFrench.exe'
& $compiler $common ('/out:'+$frenchExe) (Join-Path $build 'TestsFrench.cs')
if ($LASTEXITCODE -ne 0) { throw 'Compilation tests langue impossible.' }
& $frenchExe $build $packs
if ($LASTEXITCODE -ne 0) { throw 'Échec tests français.' }
$integration = [IO.File]::ReadAllText((Join-Path $archive 'IntegrationTests.cs'))
$packLiteral = $packs.Replace('\','/')
$integration = $integration.Replace('Directory.GetFiles(Path.Combine(dir,"A-installer/markers"),"*.taco")',('Directory.GetFiles("'+$packLiteral+'","*-FR-Classement-des-succes.taco").Where(p => !Path.GetFileName(p).StartsWith("Tehs-"))'))
$integration = $integration.Replace('Path.Combine(dir,"../Forge de Tyrie/Forge-Packs/Tehs-Trails-FR-Classement-des-succes.taco")',('"'+$packLiteral+'/Tehs-Trails-FR-Classement-des-succes.taco"'))
$integrationPath = Join-Path $build 'IntegrationTests.cs'
[IO.File]::WriteAllText($integrationPath,$integration,(New-Object Text.UTF8Encoding($true)))
$integrationExe = Join-Path $build 'IntegrationTests.exe'
& $compiler $common ('/out:'+$integrationExe) $integrationPath
if ($LASTEXITCODE -ne 0) { throw 'Compilation intégration impossible.' }
& $integrationExe $build
if ($LASTEXITCODE -ne 0) { throw 'Échec intégration Terminés.' }
