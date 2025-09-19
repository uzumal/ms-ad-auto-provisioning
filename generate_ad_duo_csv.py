#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, csv, pathlib, random, string

def zero_pad(n: int, width: int) -> str:
    return str(n).zfill(width)

def gen_employee_id(idx: int) -> str:
    return f"EMP{zero_pad(idx, 6)}"

def gen_sam(idx: int) -> str:
    # sAMAccountName 20 文字制限を確実に満たす一意キー
    return f"u{zero_pad(idx, 6)}"

def gen_upn(sam: str, upn_suffix: str) -> str:
    return f"{sam}@{upn_suffix}"

def gen_mail(sam: str, mail_suffix: str) -> str:
    return f"{sam}@{mail_suffix}"

def gen_mobile(idx: int) -> str:
    # 日本の携帯風プレースホルダ（Duo用SMS/電話のダミー）
    # +8190-XXXX-YYYY のような 11 桁想定（E.164）
    tail = zero_pad(idx % 10_000_000, 7)  # 7桁
    return f"+8190{tail}"

def gen_unique_given_name(idx: int) -> str:
    """完全一意な名前を生成"""
    base_names = [
        "Taro", "Hanako", "Ken", "Yui", "Sota", "Aoi", "Daichi", "Mina", "Haruto", "Sakura",
        "Kento", "Rina", "Yuta", "Miu", "Ren", "Mei", "Shota", "Hana", "Kaito", "Nao",
        "Hiroshi", "Akiko", "Masato", "Yuki", "Takeshi", "Mariko", "Shinji", "Kumiko", "Kenji", "Noriko",
        "Satoshi", "Michiko", "Kazuo", "Reiko", "Hideki", "Junko", "Tetsuya", "Naoko", "Yoshiaki", "Tomoko",
        "Makoto", "Sayuri", "Noboru", "Emiko", "Osamu", "Chieko", "Minoru", "Kyoko", "Isamu", "Yasuko"
    ]
    
    # 基本名前を循環使用し、インデックスで一意性を保証
    base_idx = (idx - 1) % len(base_names)
    base_name = base_names[base_idx]
    
    # 連番を追加して完全一意化
    unique_suffix = zero_pad(idx, 6)
    return f"{base_name}{unique_suffix}"

def gen_unique_surname(idx: int) -> str:
    """完全一意な姓を生成"""
    base_surnames = [
        "Yamada", "Suzuki", "Sato", "Tanaka", "Takahashi", "Ito", "Watanabe", "Nakamura", "Kobayashi", "Kato",
        "Yoshida", "Yamaguchi", "Matsumoto", "Inoue", "Kimura", "Hayashi", "Shimizu", "Saito", "Sasaki", "Yamazaki",
        "Yamamoto", "Abe", "Kondo", "Yamashita", "Sasaki", "Matsui", "Imai", "Sakamoto", "Endo", "Aoki",
        "Fujii", "Nishimura", "Fukuda", "Ota", "Miura", "Fujiwara", "Okada", "Goto", "Hasegawa", "Murakami",
        "Kondo", "Ishikawa", "Nakajima", "Ogawa", "Ishida", "Higashi", "Harada", "Morimoto", "Miyazaki", "Takeda"
    ]
    
    # 基本姓を循環使用し、インデックスで一意性を保証
    base_idx = (idx - 1) % len(base_surnames)
    base_surname = base_surnames[base_idx]
    
    # 連番を追加して完全一意化
    unique_suffix = zero_pad(idx, 6)
    return f"{base_surname}{unique_suffix}"

def gen_display_name(given: str, surname: str) -> str:
    return f"{given} {surname}".strip()

def build_name_pools():
    # 部署とロケーションのプールを拡張
    departments = [
        "Sales", "IT", "HR", "Finance", "Mfg", "Ops", "R&D", "Support",
        "Marketing", "Legal", "Procurement", "QA", "Security", "Training",
        "Accounting", "Planning", "Design", "Engineering", "Consulting", "Analytics"
    ]
    locations = [
        "Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo", "Sendai", "Kawasaki", "Yokohama",
        "Kyoto", "Kobe", "Hiroshima", "Kitakyushu", "Chiba", "Sakai", "Niigata", "Hamamatsu",
        "Kumamoto", "Sagamihara", "Okayama", "Hachioji"
    ]
    return departments, locations

def main():
    ap = argparse.ArgumentParser(description="Generate bulk AD/Duo CSVs with unique names")
    ap.add_argument("--count", type=int, default=56000, help="number of users to generate")
    ap.add_argument("--domain", required=True, help="AD domain, e.g., root.dev")
    ap.add_argument("--upn-suffix", required=True, help="UPN suffix, e.g., root.dev")
    ap.add_argument("--user-ou", required=True, help='User OU DN, e.g., OU=dev,DC=root,DC=dev')
    ap.add_argument("--group-ou", required=True, help='Group OU DN, e.g., OU=dev,DC=root,DC=dev')
    ap.add_argument("--default-password", default="P@ssw0rd1", help="Initial password placed in users.csv")
    ap.add_argument("--existing-group", action="append", default=[], help="Existing group(s) every user should join (repeatable)")
    ap.add_argument("--auto-groups", type=int, default=5, help="Number of additional groups to auto-create and balance members across (0 to disable)")
    ap.add_argument("--outdir", default=".", help="Output directory")
    ap.add_argument("--start-index", type=int, default=1, help="Start index (useful when splitting runs)")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    users_out   = outdir / "users.csv"
    groups_out  = outdir / "groups.csv"
    members_out = outdir / "group_membership.csv"

    dept_pool, loc_pool = build_name_pools()

    # 準備：グループ集合
    groups = set()
    # 既存グループはそのまま使う（定義行も出しておくと取り回しが良い）
    for g in args.existing_group:
        if g.strip():
            groups.add(g.strip())

    # 自動作成グループ
    auto_group_names = []
    if args.auto_groups > 0:
        auto_group_names = [f"GG-{str(i).zfill(2)}" for i in range(1, args.auto_groups + 1)]
        groups.update(auto_group_names)

    # --- 出力ファイル open ---
    user_headers = [
        "SamAccountName","GivenName","Surname","DisplayName","UPN","OU",
        "InitialPassword","Email","Department","Mobile","EmployeeID","Domain"
    ]
    group_headers = ["Name","SamAccountName","GroupScope","GroupCategory","OU"]
    mem_headers   = ["GroupSam","MemberSam"]

    # 一意性チェック用のセット（デバッグ用）
    used_given_names = set()
    used_surnames = set()
    used_display_names = set()
    used_upns = set()
    used_emails = set()

    # 逐次書き込み（56kでも低メモリ）
    with users_out.open("w", encoding="utf-8", newline="") as fu, \
         groups_out.open("w", encoding="utf-8", newline="") as fg, \
         members_out.open("w", encoding="utf-8", newline="") as fm:

        uw = csv.DictWriter(fu, fieldnames=user_headers); uw.writeheader()
        gw = csv.DictWriter(fg, fieldnames=group_headers); gw.writeheader()
        mw = csv.DictWriter(fm, fieldnames=mem_headers);   mw.writeheader()

        # グループ定義を書き出し（既存グループも含めて "ある体" でOK／存在すれば作成スキップ想定）
        for g in sorted(groups):
            gw.writerow({
                "Name": g,
                "SamAccountName": g,
                "GroupScope": "Global",
                "GroupCategory": "Security",
                "OU": args.group_ou
            })

        # ユーザー生成＆メンバーシップ
        auto_groups_cycle = auto_group_names if auto_group_names else []
        ag_len = len(auto_groups_cycle)

        for i in range(args.start_index, args.start_index + args.count):
            # 基本属性（一意性保証済み）
            sam  = gen_sam(i)                             # 一意な sAM（u000001 形式）
            upn  = gen_upn(sam, args.upn_suffix)         # samベースなので一意
            mail = gen_mail(sam, args.upn_suffix)        # samベースなので一意
            emp  = gen_employee_id(i)
            mob  = gen_mobile(i)

            # 完全一意な人名生成
            given = gen_unique_given_name(i)             # 完全一意
            surname = gen_unique_surname(i)              # 完全一意
            display = gen_display_name(given, surname)   # 完全一意

            dept = dept_pool[i % len(dept_pool)]
            loc  = loc_pool[(i * 3) % len(loc_pool)]

            # 一意性チェック（デバッグ用）
            if given in used_given_names:
                print(f"WARNING: Duplicate given name: {given}")
            if surname in used_surnames:
                print(f"WARNING: Duplicate surname: {surname}")
            if display in used_display_names:
                print(f"WARNING: Duplicate display name: {display}")
            if upn in used_upns:
                print(f"WARNING: Duplicate UPN: {upn}")
            if mail in used_emails:
                print(f"WARNING: Duplicate email: {mail}")

            used_given_names.add(given)
            used_surnames.add(surname)
            used_display_names.add(display)
            used_upns.add(upn)
            used_emails.add(mail)

            # users.csv
            uw.writerow({
                "SamAccountName": sam,
                "GivenName": given,
                "Surname": surname,
                "DisplayName": display,
                "UPN": upn,
                "OU": args.user_ou,
                "InitialPassword": args.default_password,
                "Email": mail,
                "Department": dept,
                "Mobile": mob,
                "EmployeeID": emp,
                "Domain": args.domain
            })

            # group_membership.csv
            # 既存グループ（全員）
            for g in args.existing_group:
                g = g.strip()
                if g:
                    mw.writerow({"GroupSam": g, "MemberSam": sam})

            # 自動グループ（均等配分）
            if ag_len > 0:
                gidx = (i - args.start_index) % ag_len
                mw.writerow({"GroupSam": auto_groups_cycle[gidx], "MemberSam": sam})

    print(f"[OK] users:  {users_out}")
    print(f"[OK] groups: {groups_out}")
    print(f"[OK] membership: {members_out}")
    print(f"[INFO] Generated {args.count} unique users")
    print(f"[INFO] Unique given names: {len(used_given_names)}")
    print(f"[INFO] Unique surnames: {len(used_surnames)}")
    print(f"[INFO] Unique display names: {len(used_display_names)}")
    print("Import order: groups.csv → users.csv → group_membership.csv")

if __name__ == "__main__":
    main()