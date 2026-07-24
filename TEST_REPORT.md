# VM Tagger — Test Report

**Date:** 2026-07-24
**Tester:** Ricardo Trentin
**Tool version:** main / ce2ee0a (warn-logging patch applied)
**Input file:** `samples/test_run2.csv`
**Status:** COMPLETED — test resources deprovisioned

---

## Infrastructure Created

### Azure
| VM Name | Resource Group | Subscription | Size |
|---------|---------------|--------------|------|
| tagger-test-vm1 | vm-tagger-test-rg2 | 47ab116c (csp_azure_rtrentin) | Standard_B1s |
| tagger-test-vm2 | vm-tagger-test-rg2 | 47ab116c (csp_azure_rtrentin) | Standard_B1s |
| tagger-test-vm3 | vm-tagger-test-rg2 | 47ab116c (csp_azure_rtrentin) | Standard_B1s |

### AWS
| Name | Instance ID | Region | Type |
|------|-------------|--------|------|
| tagger-test-ec2-1 | i-023d925821f89e86c | us-east-2 | t3.micro |
| tagger-test-ec2-2 | i-01aff7e1491b204ad | us-east-2 | t3.micro |
| tagger-test-ec2-3 | i-04978fdedbac84ecb | us-east-2 | t3.micro |

---

## Test Scenarios

| # | Cloud | VM | Tags in CSV | Scenario |
|---|-------|----|-------------|----------|
| 1 | Azure | tagger-test-vm1 | 4 tags | Multiple tags, Azure by name |
| 2 | Azure | tagger-test-vm2 | 2 tags | Minimal tags, Azure by name |
| 3 | Azure | tagger-test-vm3 | 3 tags | Mixed tags, Azure by name |
| 4 | Azure | tagger-test-vm-DOESNOTEXIST | 2 tags | **Error path** — VM does not exist |
| 5 | AWS | tagger-test-ec2-1 | 4 tags | Multiple tags, AWS by Name tag |
| 6 | AWS | i-01aff7e1491b204ad | 3 tags | AWS by instance ID |
| 7 | AWS | i-04978fdedbac84ecb | 4 tags | AWS by instance ID, different tags |
| 8 | Azure | tagger-test-vm1 | `EmptyValue=` | **Warn path** — empty tag value skipped |

---

## Dry-Run Results

```
[WARN] line 9 (tagger-test-vm1): empty value for key 'EmptyValue'
Loaded 8 VM(s) from samples/test_run2.csv
DRY-RUN mode — no changes will be applied

[OK ] AZURE tagger-test-vm1                          [DRY-RUN] would apply 4 tag(s): Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AZURE tagger-test-vm2                          [DRY-RUN] would apply 2 tag(s): Environment=Staging  Owner=OIT-Cloud
[OK ] AZURE tagger-test-vm3                          [DRY-RUN] would apply 3 tag(s): Environment=Dev  Owner=OIT-Cloud  CostCenter=456
[OK ] AZURE tagger-test-vm-DOESNOTEXIST              [DRY-RUN] would apply 2 tag(s): Environment=Production  Owner=OIT-Cloud
[OK ] AWS   tagger-test-ec2-1                        [DRY-RUN] would apply 4 tag(s): Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AWS   i-01aff7e1491b204ad                      [DRY-RUN] would apply 3 tag(s): Environment=Staging  Owner=OIT-Cloud  Team=Research
[OK ] AWS   i-04978fdedbac84ecb                      [DRY-RUN] would apply 4 tag(s): Environment=Dev  CostCenter=456  Department=Engineering  Team=Platform
[OK ] AZURE tagger-test-vm1                          [DRY-RUN] would apply 2 tag(s): Environment=Production  Owner=OIT-Cloud

Done — 8 succeeded, 0 failed
```

**Result:** PASS — all rows parsed and previewed correctly. [WARN] fired on empty value and was excluded from tag dict.

---

## Live Run Results

```
[WARN] line 9 (tagger-test-vm1): empty value for key 'EmptyValue'
Loaded 8 VM(s) from samples/test_run2.csv

[OK ] AZURE tagger-test-vm1                          Applied 4 tag(s): Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AZURE tagger-test-vm2                          Applied 2 tag(s): Environment=Staging  Owner=OIT-Cloud
[OK ] AZURE tagger-test-vm3                          Applied 3 tag(s): Environment=Dev  Owner=OIT-Cloud  CostCenter=456
[ERR] AZURE tagger-test-vm-DOESNOTEXIST              (ResourceNotFound) The Resource 'Microsoft.Compute/virtualMachines/tagger-test-vm-DOESNOTEXIST' under resource group 'vm-tagger-test-rg2' was not found.
[OK ] AWS   tagger-test-ec2-1                        Applied 4 tag(s) to ['i-023d925821f89e86c']: Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AWS   i-01aff7e1491b204ad                      Applied 3 tag(s) to ['i-01aff7e1491b204ad']: Environment=Staging  Owner=OIT-Cloud  Team=Research
[OK ] AWS   i-04978fdedbac84ecb                      Applied 4 tag(s) to ['i-04978fdedbac84ecb']: Environment=Dev  CostCenter=456  Department=Engineering  Team=Platform
[OK ] AZURE tagger-test-vm1                          Applied 2 tag(s): Environment=Production  Owner=OIT-Cloud

Done — 7 succeeded, 1 failed
```

**Result:** PASS — 7/7 real VMs tagged, 1 expected error on non-existent VM. Empty-value tag correctly excluded.

---

## Tag Verification

### Azure (confirmed via `az vm show --query tags`)

| VM | Tags Applied |
|----|-------------|
| tagger-test-vm1 | Environment=Production, Owner=OIT-Cloud, CostCenter=123, Project=VMTaggerTest |
| tagger-test-vm2 | Environment=Staging, Owner=OIT-Cloud |
| tagger-test-vm3 | Environment=Dev, Owner=OIT-Cloud, CostCenter=456 |

Note: row 8 (`EmptyValue=`) issued a [WARN] and was excluded — final applied tags on vm1 matched row 1, confirming empty values do not pollute the tag dict.

### AWS (confirmed via `aws ec2 describe-instances`)

| Instance ID | Name | Tags Applied |
|-------------|------|-------------|
| i-023d925821f89e86c | tagger-test-ec2-1 | Environment=Production, Owner=OIT-Cloud, CostCenter=123, Project=VMTaggerTest, Name=tagger-test-ec2-1 (pre-existing) |
| i-01aff7e1491b204ad | tagger-test-ec2-2 | Environment=Staging, Owner=OIT-Cloud, Team=Research, Name=tagger-test-ec2-2 (pre-existing) |
| i-04978fdedbac84ecb | tagger-test-ec2-3 | Environment=Dev, CostCenter=456, Department=Engineering, Team=Platform, Name=tagger-test-ec2-3 (pre-existing) |

**Pre-existing `Name` tags were preserved** — merge behavior confirmed.

---

## Deprovisioning

Test resources terminated on 2026-07-24 after test completion.

| Cloud | Resource | Action |
|-------|----------|--------|
| Azure | vm-tagger-test-rg2 (+ all 3 VMs) | Resource group deleted (`--no-wait`) |
| AWS | i-023d925821f89e86c, i-01aff7e1491b204ad, i-04978fdedbac84ecb | Instances terminated (us-east-2) |

---

## Issues Found & Fixed

| # | Issue | Fix |
|---|-------|-----|
| 1 | `AWS_PROFILE=claude-bedrock` in shell env caused boto3 to use expired SSO token | Clear `AWS_PROFILE` at startup; use `AWS_PROFILE_KEEP=1` to override. Fixed in e2c2370. |
| 2 | Empty-value tags (`key=`) silently passed through into the tag dict | `_parse_tags` now rejects empty values and emits `[WARN]` via `_parse_record`. |

---

## Summary

| Scenario | Result |
|----------|--------|
| Azure — tag by VM name (multiple tags) | PASS |
| Azure — tag by VM name (few tags) | PASS |
| Azure — non-existent VM error handling | PASS (clean ResourceNotFound error) |
| AWS — tag by Name tag | PASS |
| AWS — tag by instance ID | PASS |
| AWS — preserve pre-existing Name tag | PASS |
| Dry-run preview for all scenarios | PASS |
| Empty-value tag warning (`EmptyValue=`) | PASS — [WARN] emitted, tag excluded |
