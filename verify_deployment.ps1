# Verify Render Deployment Script
# Backend and Orchestrator URLs from Render

$BACKEND_URL = "https://eventai-backend-upym.onrender.com"
$ORCHESTRATOR_URL = "https://eventai-orchestrator.onrender.com"

Write-Host "🔍 Verifying Render Deployment..." -ForegroundColor Cyan
Write-Host ""

# Test Backend Health
Write-Host "Testing Backend Health Endpoint..." -ForegroundColor Yellow
try {
    $backendHealth = Invoke-RestMethod -Uri "$BACKEND_URL/api/v1/health" -Method Get
    Write-Host "✅ Backend is healthy!" -ForegroundColor Green
    Write-Host "   Response: $($backendHealth | ConvertTo-Json)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Backend health check failed!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test Orchestrator Health
Write-Host "Testing Orchestrator Health Endpoint..." -ForegroundColor Yellow
try {
    $orchestratorHealth = Invoke-RestMethod -Uri "$ORCHESTRATOR_URL/health" -Method Get
    Write-Host "✅ Orchestrator is healthy!" -ForegroundColor Green
    Write-Host "   Response: $($orchestratorHealth | ConvertTo-Json)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Orchestrator health check failed!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Update Google OAuth redirect URI in Google Cloud Console" -ForegroundColor White
Write-Host "2. Deploy frontends to Vercel" -ForegroundColor White
Write-Host "3. Update CORS_ORIGINS in Render with Vercel URLs" -ForegroundColor White
