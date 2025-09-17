Write-Host "=== Ultimele semnale și tranzacții din DB ==="
python check_db.py

Write-Host "=== Analiză performanță bot ==="
python analyze_db.py

Write-Host "=== Generare grafice evoluție ==="
python analyze_db_charts.py
