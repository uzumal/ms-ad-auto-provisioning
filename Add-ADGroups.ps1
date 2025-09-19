$groups = Import-Csv .\groups.csv
foreach ($g in $groups) {
    if (-not (Get-ADGroup -LDAPFilter "(sAMAccountName=$($g.SamAccountName))" -Server $server -ErrorAction SilentlyContinue)) {
        New-ADGroup `
          -Name $g.Name `
          -SamAccountName $g.SamAccountName `
          -GroupScope $g.GroupScope `
          -GroupCategory $g.GroupCategory `
          -Path $g.OU `
          -Server $server
        Write-Host "Created group $($g.Name)"
    } else {
        Write-Host "Skipped (already exists): $($g.Name)"
    }
}