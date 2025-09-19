$users = Import-Csv .\users.csv
foreach ($u in $users) {
    if (-not (Get-ADUser -LDAPFilter "(sAMAccountName=$($u.SamAccountName))" -Server $server -ErrorAction SilentlyContinue)) {
        $pwd = ConvertTo-SecureString $u.InitialPassword -AsPlainText -Force
        New-ADUser `
          -Name $u.DisplayName `
          -GivenName $u.GivenName `
          -Surname $u.Surname `
          -SamAccountName $u.SamAccountName `
          -UserPrincipalName $u.UPN `
          -DisplayName $u.DisplayName `
          -Path $u.OU `
          -EmailAddress $u.Email `
          -Department $u.Department `
          -MobilePhone $u.Mobile `
          -EmployeeID $u.EmployeeID `
          -AccountPassword $pwd `
          -Enabled $true `
          -ChangePasswordAtLogon $true `
          -Server $server
        Write-Host "Created user $($u.SamAccountName)"
    } else {
        Write-Host "Skipped (already exists): $($u.SamAccountName)"
    }
}