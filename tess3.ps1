# --- CONFIGURATION ---
# Script version (Semantic Versioning)
$VERSION = "1.0.0"

# Force UTF-8 encoding for proper French character handling
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$dossierSource = "C:\EchoThyr\export"
$cheminModele = "C:\EchoThyr\Modele_Echo.docx"
$largeurCible = 1200
$tesseractExe = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:TESSDATA_PREFIX = "C:\Program Files\Tesseract-OCR\tessdata" 

Add-Type -AssemblyName System.Drawing

# --- LOGGING CONFIGURATION ---
$logDir = "C:\EchoThyr\logs"
$logFile = Join-Path $logDir "tess3_$(Get-Date -Format 'yyyy-MM-dd').log"

function Initialize-Logging {
    if (!(Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('INFO', 'ERROR', 'WARNING', 'DEBUG', 'SUCCESS')]
        [string]$Level = 'INFO',
        [bool]$Console = $true
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logEntry = "[$timestamp] [$Level] $Message"

    # Write to file
    Add-Content -Path $logFile -Value $logEntry -Encoding UTF8 -Force

    # Write to console with color coding
    if ($Console) {
        $color = switch ($Level) {
            'ERROR'   { 'Red' }
            'WARNING' { 'Yellow' }
            'SUCCESS' { 'Green' }
            'DEBUG'   { 'Gray' }
            'INFO'    { 'Cyan' }
        }
        Write-Host "$logEntry" -ForegroundColor $color
    }
}

function Write-LogDebug {
    param([string]$Message)
    Write-Log -Message $Message -Level 'DEBUG' -Console $false
}

function Test-Prerequisites {
    Write-Log "Starting prerequisite validation..." -Level 'INFO'
    $validationPassed = $true

    # Test source directory
    if (!(Test-Path -Path $dossierSource -PathType Container)) {
        Write-Log "FATAL: Source directory not found: $dossierSource" -Level 'ERROR'
        $validationPassed = $false
    } else {
        Write-Log "Source directory verified: $dossierSource" -Level 'SUCCESS'
    }

    # Test template file
    if (!(Test-Path -Path $cheminModele -PathType Leaf)) {
        Write-Log "FATAL: Template file not found: $cheminModele" -Level 'ERROR'
        $validationPassed = $false
    } else {
        Write-Log "Template file verified: $cheminModele" -Level 'SUCCESS'
    }

    # Test Tesseract executable
    if (!(Test-Path -Path $tesseractExe -PathType Leaf)) {
        Write-Log "FATAL: Tesseract executable not found: $tesseractExe" -Level 'ERROR'
        $validationPassed = $false
    } else {
        Write-Log "Tesseract executable found: $tesseractExe" -Level 'SUCCESS'
    }

    # Test Tesseract installation with version check
    try {
        $tesseractVersion = & $tesseractExe --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Tesseract version check passed: $($tesseractVersion[0])" -Level 'SUCCESS'
        } else {
            Write-Log "Tesseract version check failed with exit code: $LASTEXITCODE" -Level 'ERROR'
            $validationPassed = $false
        }
    } catch {
        Write-Log "Failed to execute Tesseract version check: $($_.Exception.Message)" -Level 'ERROR'
        $validationPassed = $false
    }

    # Test TESSDATA_PREFIX environment variable
    $tessDataPath = "C:\Program Files\Tesseract-OCR\tessdata"
    if (!(Test-Path -Path $tessDataPath -PathType Container)) {
        Write-Log "WARNING: TESSDATA_PREFIX directory may not be valid: $tessDataPath" -Level 'WARNING'
    } else {
        Write-Log "TESSDATA_PREFIX verified: $tessDataPath" -Level 'SUCCESS'
    }

    if (-not $validationPassed) {
        Write-Log "FATAL: Prerequisites validation failed. Exiting script." -Level 'ERROR'
        exit 1
    }

    Write-Log "All prerequisites validated successfully. Starting monitor loop." -Level 'SUCCESS'
}

function Invoke-SuccessNotification {
    param(
        [string]$BaseName,
        [string]$PatientInfo
    )

    # Audio notification (system beep)
    [console]::Beep(800, 300)
    [console]::Beep(1200, 300)

    # Visual notification with enhanced formatting
    Write-Host "`n$('-' * 80)" -ForegroundColor Green
    Write-Host "SUCCESS: Report Generated Successfully!" -ForegroundColor Green -BackgroundColor Black
    Write-Host "-" * 80 -ForegroundColor Green
    Write-Host "Report Name    : $BaseName" -ForegroundColor Green
    Write-Host "Patient Info   : $PatientInfo" -ForegroundColor Green
    Write-Host "Generated At   : $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
    Write-Host "$('-' * 80)`n" -ForegroundColor Green

    # Log the success event
    Write-Log "Report generated successfully: $BaseName for $PatientInfo" -Level 'SUCCESS'
}

function Invoke-ErrorNotification {
    param(
        [string]$ErrorMessage,
        [string]$Context
    )

    # Audio notification (error beep pattern)
    [console]::Beep(400, 200)
    [console]::Beep(400, 200)

    # Visual notification
    Write-Host "`n$('-' * 80)" -ForegroundColor Red
    Write-Host "ERROR: Report Generation Failed" -ForegroundColor Red -BackgroundColor Black
    Write-Host "-" * 80 -ForegroundColor Red
    Write-Host "Context        : $Context" -ForegroundColor Red
    Write-Host "Error Message  : $ErrorMessage" -ForegroundColor Red
    Write-Host "Occurred At    : $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Red
    Write-Host "$('-' * 80)`n" -ForegroundColor Red

    # Log the error event
    Write-Log "Report generation failed for $Context : $ErrorMessage" -Level 'ERROR'
}

function Get-PatientInfoFromFolderName {
    param($folderName)
    $parts = $folderName.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    $info = @{ Nom = "A PRECISER"; Prenom = ""; Date = (Get-Date -Format "dd.MM.yyyy") }
    if ($parts.Count -ge 1) { $info.Nom = $parts[0].ToUpper() }
    if ($parts.Count -ge 2) { $info.Prenom = $parts[1] }
    return $info
}

function Get-Measurements {
    param($imagePath)

    Write-LogDebug "Processing image: $imagePath"

    try {
        # Validate input
        if (!(Test-Path $imagePath -PathType Leaf)) {
            Write-Log "Image file not found: $imagePath" -Level 'WARNING'
            return $null
        }

        $tempFileBase = [System.IO.Path]::GetTempFileName()
        $tempOutputFile = $tempFileBase + ".txt"

        Write-LogDebug "Executing Tesseract: $tesseractExe '$imagePath' '$tempFileBase' --psm 6 -l eng"

        # FIXED: Removed quiet parameter (not supported in all Tesseract versions)
        # Redirect stderr to null to suppress Tesseract warnings
        & $tesseractExe "$imagePath" "$tempFileBase" --psm 6 -l eng 2>$null

        # Check Tesseract exit code
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Tesseract failed with exit code $LASTEXITCODE for image: $imagePath" -Level 'WARNING'
            Write-LogDebug "Tesseract output file: $tempOutputFile"
            return $null
        }

        if (!(Test-Path $tempOutputFile)) {
            Write-Log "Tesseract output file not created for: $imagePath" -Level 'WARNING'
            return $null
        }

        $texte = Get-Content $tempOutputFile -Raw
        Remove-Item $tempOutputFile -Force -ErrorAction SilentlyContinue

        if ([string]::IsNullOrWhiteSpace($texte)) {
            Write-LogDebug "Tesseract extracted no text from: $imagePath"
            return $null
        }

        Write-LogDebug "Tesseract extracted text: $($texte.Substring(0, [Math]::Min(100, $texte.Length)))"

        # Extract measurement data
        $cote = if ($texte -match "RT|Right|Droite") { "RT" } elseif ($texte -match "LT|Left|Gauche") { "LT" } else { "" }
        $numNodule = if ($texte -match "N(\d+)") { $Matches[1] } else { "" }
        $isIsthme = $texte -match "Isthme|Isthmus"
        $valeursMM = @()

        foreach ($m in [regex]::Matches($texte, "(\d+[\.,]\d+)\s*cm")) {
            $valeurCm = [double]($m.Groups[1].Value.Replace(',', '.'))
            $valeursMM += ([math]::Round($valeurCm * 10, 1)).ToString([System.Globalization.CultureInfo]::InvariantCulture)
        }

        if ($valeursMM.Count -gt 0) {
            $mesureStr = $valeursMM -join " x "
            if ($texte -match "Vol.*?(\d+[\.,]\d+)") {
                $vol = $Matches[1].Replace(',', '.')
                $mesureStr += " mm (volume $vol ml)"
            } else { $mesureStr += " mm" }

            Write-LogDebug "Extracted measurement: Cote=$cote, Nodule=$numNodule, Isthme=$isIsthme, Mesure=$mesureStr"
            return [PSCustomObject]@{
                Cote = $cote
                Nodule = $numNodule
                Isthme = $isIsthme
                Texte = $mesureStr
            }
        } else {
            Write-LogDebug "No measurements extracted from: $imagePath"
            return $null
        }
    } catch {
        Write-Log "Exception in Get-Measurements for image $imagePath : $($_.Exception.Message)" -Level 'ERROR'
        Write-LogDebug "Stack trace: $($_.ScriptStackTrace)"
        return $null
    }
}

# Initialize logging system
Initialize-Logging
Write-Log "Script started - Version $VERSION" -Level 'INFO'
Write-Log "Configuration - Source: $dossierSource, Template: $cheminModele, Tesseract: $tesseractExe" -Level 'INFO'

# Perform startup validation
Test-Prerequisites

$dossiersInitiaux = Get-ChildItem -Path $dossierSource -Directory -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ECHOTHYR AUTOMATION - MONITORING CR ECHO THYR GENERATION        v$VERSION  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source Directory: $dossierSource" -ForegroundColor Cyan
Write-Host "Template File   : $cheminModele" -ForegroundColor Cyan
Write-Host "Log File        : $logFile" -ForegroundColor Cyan
Write-Host "Monitoring start: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
Write-Host "-" * 80 -ForegroundColor Cyan

while($true) {
    try {
        Write-LogDebug "Checking for new folders at: $dossierSource"

        $nouveauxDossiers = Get-ChildItem -Path $dossierSource -Directory -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $dossiersInitiaux -notcontains $_.FullName }

        if ($nouveauxDossiers.Count -gt 0) {
            Write-Log "Found $($nouveauxDossiers.Count) new folder(s) to process" -Level 'INFO'
        }

        foreach ($dossier in $nouveauxDossiers) {
            Write-Log "Processing folder: $($dossier.Name)" -Level 'INFO'

            try {
                # --- RÉCUPÉRATION DES INFOS ---
                $patient = Get-PatientInfoFromFolderName -folderName $dossier.Name
                Write-LogDebug "Patient info extracted - Name: $($patient.Nom), First: $($patient.Prenom), Date: $($patient.Date)"

                # Nettoyage de la date pour le nom de fichier
                $dateFile = $patient.Date -replace '\.', '-'
                $baseName = "CR ECHO THYR $($patient.Nom) $($patient.Prenom) $dateFile"

                $wordPath = [string](Join-Path $dossier.FullName "$baseName.docx")
                $pdfPath = [string](Join-Path $dossier.FullName "$baseName.pdf")

                if (Test-Path $wordPath) {
                    Write-LogDebug "Report already exists for patient: $($patient.Nom) $($patient.Prenom)"
                    continue
                }

                $fichiers = Get-ChildItem -Path $dossier.FullName -Filter "*.jpg" -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -notlike "$*" }

                if ($fichiers.Count -eq 0) {
                    Write-LogDebug "No image files found in folder: $($dossier.FullName)"
                    continue
                }

                Write-Log "Found $($fichiers.Count) image file(s) for processing" -Level 'INFO'

                $listeMesures = @()
                $imagesTraitees = @()

                foreach ($file in $fichiers) {
                    $nouveauNom = Join-Path $file.DirectoryName ("$" + $file.BaseName + ".jpg")

                    Write-LogDebug "Processing image file: $($file.Name)"

                    $res = Get-Measurements -imagePath $file.FullName
                    if ($null -ne $res) { $listeMesures += $res }

                    try {
                        Write-LogDebug "Resizing image: $($file.FullName) -> Width=$largeurCible"

                        $img = [System.Drawing.Image]::FromFile($file.FullName)
                        $ratio = $largeurCible / $img.Width
                        $bmp = New-Object System.Drawing.Bitmap($largeurCible, [int]($img.Height * $ratio))
                        $graph = [System.Drawing.Graphics]::FromImage($bmp)
                        $graph.InterpolationMode = 7
                        $graph.DrawImage($img, 0, 0, $bmp.Width, $bmp.Height)

                        $img.Dispose()
                        $bmp.Save($nouveauNom, [System.Drawing.Imaging.ImageFormat]::Jpeg)
                        $bmp.Dispose()
                        $graph.Dispose()

                        $imagesTraitees += $nouveauNom
                        Write-LogDebug "Image resized successfully: $nouveauNom"

                    } catch {
                        Write-Log "Failed to resize image $($file.FullName): $($_.Exception.Message)" -Level 'WARNING'
                        Write-LogDebug "Image processing stack trace: $($_.ScriptStackTrace)"

                        # Ensure proper cleanup even on error
                        if ($img) { $img.Dispose() }
                        if ($bmp) { $bmp.Dispose() }
                        if ($graph) { $graph.Dispose() }
                    }
                }

                if ($listeMesures.Count -eq 0) {
                    Write-Log "No measurements extracted from images - skipping report generation for: $($patient.Nom) $($patient.Prenom)" -Level 'WARNING'
                    continue
                }

                Write-Log "Extracted $($listeMesures.Count) measurement(s) - generating Word document" -Level 'INFO'

                $Word = $null
                $Doc = $null

                try {
                    $Word = New-Object -ComObject Word.Application
                    $Word.Visible = $false
                    $Doc = $Word.Documents.Open($cheminModele)

                    function Set-Bookmark ($name, $content) {
                        if ($Doc.Bookmarks.Exists($name)) {
                            $range = $Doc.Bookmarks.Item($name).Range
                            $range.Text = $content
                            $Doc.Bookmarks.Add($name, $range) | Out-Null
                            Write-LogDebug "Bookmark set: $name = $content"
                        } else {
                            Write-Log "Bookmark not found in template: $name" -Level 'WARNING'
                        }
                    }

                    Set-Bookmark "NOM" $patient.Nom
                    Set-Bookmark "PRENOM" $patient.Prenom
                    Set-Bookmark "DATE" $patient.Date

                    $valD = ($listeMesures | Where-Object { $_.Cote -eq "RT" -and -not $_.Nodule -and -not $_.Isthme } | Select-Object -First 1).Texte
                    if (!$valD) { $valD = "non mesuré" }
                    $valG = ($listeMesures | Where-Object { $_.Cote -eq "LT" -and -not $_.Nodule -and -not $_.Isthme } | Select-Object -First 1).Texte
                    if (!$valG) { $valG = "non mesuré" }
                    $valI = ($listeMesures | Where-Object { $_.Isthme } | Select-Object -First 1).Texte
                    if (!$valI) { $valI = "non mesuré" }

                    Write-LogDebug "Measurements - Right: $valD, Left: $valG, Isthme: $valI"

                    $txtCR = "• Volume thyroïdien`r`n- lobe droit : $valD`r`n- lobe gauche : $valG`r`n- isthme : $valI`r`n"
                    $txtCR += "• Echogénicité glandulaire homogène`r`n• Pas d'anomalie de la vascularisation`r`n• Nodules :`r`n"
                    foreach ($nod in ($listeMesures | Where-Object { $_.Nodule -ne "" })) {
                        $loc = if ($nod.Cote -eq "RT") { "Lobe droit" } else { "Lobe gauche" }
                        $txtCR += "  - Nodule N$($nod.Nodule) $loc : $($nod.Texte)`r`n"
                    }
                    $txtCR += "• Etude des ganglions (secteurs II, III, IV, VI) et du tractus thyréoglosse : 0"

                    Set-Bookmark "RESULTAT" $txtCR

                    Write-LogDebug "Adding images to document. Total images: $($imagesTraitees.Count)"

                    $Doc.Characters.Last.Select()
                    $Word.Selection.InsertBreak(7)
                    foreach ($imgPath in $imagesTraitees) {
                        $Word.Selection.InlineShapes.AddPicture($imgPath) | Out-Null
                        $Word.Selection.TypeText("`r`n")
                    }

                    Write-Log "Saving Word document: $wordPath" -Level 'INFO'
                    $Doc.SaveAs2($wordPath, 16)

                    Write-Log "Exporting PDF: $pdfPath" -Level 'INFO'
                    $Doc.ExportAsFixedFormat($pdfPath, 17)

                    # Invoke success notification
                    $patientInfo = "$($patient.Nom) $($patient.Prenom) ($($patient.Date))"
                    Invoke-SuccessNotification -BaseName $baseName -PatientInfo $patientInfo

                    # Add to tracking list
                    $dossiersInitiaux += $dossier.FullName

                } catch {
                    $errorMsg = $_.Exception.Message
                    Write-Log "Exception during Word document generation: $errorMsg" -Level 'ERROR'
                    Write-LogDebug "Stack trace: $($_.ScriptStackTrace)"

                    $patientInfo = "$($patient.Nom) $($patient.Prenom)"
                    Invoke-ErrorNotification -ErrorMessage $errorMsg -Context $patientInfo

                } finally {
                    # Ensure cleanup
                    if ($Doc) {
                        try { $Doc.Close() } catch { Write-LogDebug "Error closing Word document: $_" }
                    }
                    if ($Word) {
                        try {
                            $Word.Quit()
                            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Word) | Out-Null
                        } catch {
                            Write-LogDebug "Error closing Word application: $_"
                        }
                    }
                }

            } catch {
                Write-Log "Unexpected error processing folder $($dossier.FullName): $($_.Exception.Message)" -Level 'ERROR'
                Write-LogDebug "Full stack trace: $($_.ScriptStackTrace)"
            }
        }

        Write-LogDebug "Monitoring loop cycle complete. Next check in 10 seconds."
        Start-Sleep -Seconds 10

    } catch {
        Write-Log "Critical error in main loop: $($_.Exception.Message)" -Level 'ERROR'
        Write-LogDebug "Critical stack trace: $($_.ScriptStackTrace)"
        Start-Sleep -Seconds 10
    }
}