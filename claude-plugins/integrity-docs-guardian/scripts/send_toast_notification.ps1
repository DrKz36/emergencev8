# ============================================================================
# GUARDIAN TOAST NOTIFICATIONS - Windows 10/11
# ============================================================================
# Envoie des notifications toast natives Windows pour les alertes Guardian
# Usage: .\send_toast_notification.ps1 -Title "Guardian Alert" -Message "Critical issue detected" -Severity "critical"
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$Title,

    [Parameter(Mandatory=$true)]
    [string]$Message,

    [Parameter(Mandatory=$false)]
    [ValidateSet("ok", "warning", "critical", "info")]
    [string]$Severity = "info",

    [Parameter(Mandatory=$false)]
    [string]$ReportPath = ""
)

# Icons basés sur severity
$iconMap = @{
    "ok" = "✅"
    "info" = "ℹ️"
    "warning" = "⚠️"
    "critical" = "🚨"
}

$icon = $iconMap[$Severity]
$fullTitle = "$icon $Title"

# Déterminer le son
$sound = switch ($Severity) {
    "critical" { "ms-winsoundevent:Notification.Looping.Alarm" }
    "warning"  { "ms-winsoundevent:Notification.Default" }
    default    { "ms-winsoundevent:Notification.Mail" }
}

# Construire le XML pour le toast
$toastXml = @"
<toast launch="action=viewReport&amp;path=$ReportPath">
    <visual>
        <binding template="ToastGeneric">
            <text>$fullTitle</text>
            <text>$Message</text>
        </binding>
    </visual>
    <audio src="$sound" />
</toast>
"@

try {
    # Charger les assemblies nécessaires
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    # Créer le toast
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($toastXml)

    # Définir l'App ID (utiliser PowerShell ou créer un custom)
    $appId = "Emergence.Guardian"

    # Créer et afficher la notification
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId)
    $notifier.Show($toast)

    Write-Host "✅ Toast notification sent: $fullTitle" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "❌ Failed to send toast notification: $_" -ForegroundColor Red

    # Fallback: Utiliser popup classique Windows
    Add-Type -AssemblyName System.Windows.Forms
    $result = [System.Windows.Forms.MessageBox]::Show($Message, $fullTitle, "OK", "Information")

    exit 1
}
