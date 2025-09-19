param(
    [Parameter(Mandatory=$true)]
    [string]$server
)

# エラー発生時に停止
$ErrorActionPreference = "Stop"

try {
    Write-Host "=== AD Group Membership Import Script ===" -ForegroundColor Green
    Write-Host "Server: $server"
    Write-Host "Start Time: $(Get-Date)"
    
    # 1. ハッシュテーブル初期化（デバッグ情報付き）
    Write-Host "`n[Step 1] Initializing user lookup table..." -ForegroundColor Yellow
    $userLookup = @{}
    Write-Host "Hash table initialized. Type: $($userLookup.GetType().Name)"
    
    # 2. 全ユーザー取得（改良版）
    Write-Host "`n[Step 2] Loading all users from AD..." -ForegroundColor Yellow
    try {
        # より具体的なフィルターとプロパティ指定
        $allUsers = Get-ADUser -Filter "SamAccountName -like 'u*'" -Server $server -Properties SamAccountName,DistinguishedName
        Write-Host "Successfully retrieved $($allUsers.Count) users from AD"
        
        if ($allUsers.Count -eq 0) {
            Write-Warning "No users found matching filter 'SamAccountName -like u*'"
            Write-Host "Trying alternative filter..."
            $allUsers = Get-ADUser -Filter * -Server $server -Properties SamAccountName,DistinguishedName | Where-Object { $_.SamAccountName -like "u*" }
            Write-Host "Alternative method found $($allUsers.Count) users"
        }
    }
    catch {
        Write-Error "Failed to retrieve users from AD: $($_.Exception.Message)"
        exit 1
    }
    
    # 3. ハッシュテーブル構築
    Write-Host "`n[Step 3] Building user lookup table..." -ForegroundColor Yellow
    $userCount = 0
    foreach ($user in $allUsers) {
        if ($user.SamAccountName -and $user.DistinguishedName) {
            $userLookup[$user.SamAccountName] = $user.DistinguishedName
            $userCount++
        }
        else {
            Write-Warning "User with missing SamAccountName or DN: $($user | ConvertTo-Json -Compress)"
        }
    }
    Write-Host "Loaded $userCount users into lookup table"
    
    # ハッシュテーブルの状態確認
    if ($userLookup -eq $null) {
        Write-Error "User lookup table is null!"
        exit 1
    }
    
    Write-Host "Hash table sample (first 5 entries):"
    $userLookup.GetEnumerator() | Select-Object -First 5 | ForEach-Object {
        Write-Host "  $($_.Key) -> $($_.Value)"
    }
    
    # 4. CSVファイル読み込み
    Write-Host "`n[Step 4] Loading group membership CSV..." -ForegroundColor Yellow
    if (-not (Test-Path ".\group_membership.csv")) {
        Write-Error "group_membership.csv not found in current directory"
        exit 1
    }
    
    $membershipData = Import-Csv .\group_membership.csv
    Write-Host "Loaded $($membershipData.Count) membership records"
    
    # グループ別にグループ化
    $map = $membershipData | Group-Object GroupSam
    Write-Host "Found $($map.Count) unique groups"
    
    # 5. グループメンバーシップ処理
    Write-Host "`n[Step 5] Processing group memberships..." -ForegroundColor Yellow
    $totalGroups = $map.Count
    $currentGroup = 0
    $totalProcessed = 0
    $totalErrors = 0
    
    foreach ($grp in $map) {
        $currentGroup++
        $g = $grp.Name
        Write-Host "`n[$currentGroup/$totalGroups] Processing group: $g" -ForegroundColor Cyan
        
        # グループの存在確認
        try {
            $adGroup = Get-ADGroup -Identity $g -Server $server
            Write-Host "  Group exists: $($adGroup.DistinguishedName)"
        }
        catch {
            Write-Warning "  Group $g not found, skipping..."
            continue
        }
        
        # 既存メンバー取得
        try {
            $existingMembers = (Get-ADGroupMember -Identity $g -Server $server).SamAccountName
            Write-Host "  Existing members: $($existingMembers.Count)"
        }
        catch {
            Write-Warning "  Could not get existing members for $g"
            $existingMembers = @()
        }
        
        # 新規追加対象の特定
        $requestedMembers = $grp.Group | ForEach-Object { $_.MemberSam } | Sort-Object -Unique
        $newMembers = $requestedMembers | Where-Object { $_ -notin $existingMembers }
        
        Write-Host "  Requested: $($requestedMembers.Count), New: $($newMembers.Count)"
        
        if ($newMembers.Count -eq 0) {
            Write-Host "  No new members to add, skipping" -ForegroundColor Gray
            continue
        }
        
        # DN変換（改良版エラーハンドリング）
        $validDNs = @()
        $invalidMembers = @()
        
        foreach ($member in $newMembers) {
            if ([string]::IsNullOrEmpty($member)) {
                Write-Warning "  Empty member name found, skipping"
                continue
            }
            
            if ($userLookup.ContainsKey($member)) {
                $validDNs += $userLookup[$member]
            }
            else {
                $invalidMembers += $member
            }
        }
        
        Write-Host "  Valid DNs: $($validDNs.Count), Invalid members: $($invalidMembers.Count)"
        
        if ($invalidMembers.Count -gt 0) {
            Write-Warning "  Invalid members: $($invalidMembers -join ', ')"
        }
        
        if ($validDNs.Count -eq 0) {
            Write-Warning "  No valid members to add"
            continue
        }
        
        # バッチ処理
        $chunk = 500
        $batchCount = [math]::Ceiling($validDNs.Count / $chunk)
        
        for ($i = 0; $i -lt $validDNs.Count; $i += $chunk) {
            $batchNum = [math]::Floor($i / $chunk) + 1
            $endIndex = [math]::Min($i + $chunk - 1, $validDNs.Count - 1)
            $batch = $validDNs[$i..$endIndex]
            
            Write-Host "    Batch $batchNum/$batchCount ($($batch.Count) members)..." -NoNewline
            
            try {
                Add-ADGroupMember -Identity $g -Members $batch -Server $server -ErrorAction Stop
                Write-Host " ✓" -ForegroundColor Green
                $totalProcessed += $batch.Count
            }
            catch {
                Write-Host " ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
                $totalErrors += $batch.Count
            }
            
            # 負荷軽減
            Start-Sleep -Milliseconds 200
        }
    }
    
    # 完了報告
    Write-Host "`n=== Processing Complete ===" -ForegroundColor Green
    Write-Host "Total processed: $totalProcessed"
    Write-Host "Total errors: $totalErrors"
    Write-Host "End Time: $(Get-Date)"
    
}
catch {
    Write-Error "Script failed: $($_.Exception.Message)"
    Write-Error "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}

# 実行例:
# .\script.ps1 -server "your-domain-controller.domain.com"