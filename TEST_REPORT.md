# VM Tagger — Test Report

**Date:** 2026-07-24
**Tester:** Ricardo Trentin
**Tool version:** main / e2c2370
**Input file:** `samples/test_run.csv`

---

## Infrastructure Created

### Azure
| VM Name | Resource Group | Subscription | Size |
|---------|---------------|--------------|------|
| tagger-test-vm1 | vm-tagger-test-rg | 47ab116c (csp_azure_rtrentin) | Standard_B1s |
| tagger-test-vm2 | vm-tagger-test-rg | 47ab116c (csp_azure_rtrentin) | Standard_B1s |
| tagger-test-vm3 | vm-tagger-test-rg | 47ab116c (csp_azure_rtrentin) | Standard_B1s |

### AWS
| Name | Instance ID | Region | Type |
|------|-------------|--------|------|
| tagger-test-ec2-1 | i-0f4b9dddc1b2204d2 | us-east-2 | t3.micro |
| tagger-test-ec2-2 | i-02f85514dc2a56857 | us-east-2 | t3.micro |
| tagger-test-ec2-3 | i-0569ff04a074f4780 | us-east-2 | t3.micro |

---

## Test Scenarios

| # | Cloud | VM | Tags in CSV | Scenario |
|---|-------|----|-------------|----------|
| 1 | Azure | tagger-test-vm1 | 4 tags | Multiple tags, Azure by name |
| 2 | Azure | tagger-test-vm2 | 2 tags | Minimal tags, Azure by name |
| 3 | Azure | tagger-test-vm3 | 3 tags | Mixed tags, Azure by name |
| 4 | Azure | tagger-test-vm-DOESNOTEXIST | 2 tags | **Error path** — VM does not exist |
| 5 | AWS | tagger-test-ec2-1 | 4 tags | Multiple tags, AWS by Name tag |
| 6 | AWS | i-02f85514dc2a56857 | 3 tags | AWS by instance ID |
| 7 | AWS | i-0569ff04a074f4780 | 4 tags | AWS by instance ID, different tags |

---

## Dry-Run Results

```
Loaded 7 VM(s) from samples/test_run.csv
DRY-RUN mode — no changes will be applied

[OK ] AZURE tagger-test-vm1           [DRY-RUN] would apply 4 tag(s): Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AZURE tagger-test-vm2           [DRY-RUN] would apply 2 tag(s): Environment=Staging  Owner=OIT-Cloud
[OK ] AZURE tagger-test-vm3           [DRY-RUN] would apply 3 tag(s): Environment=Dev  Owner=OIT-Cloud  CostCenter=456
[OK ] AZURE tagger-test-vm-DOESNOTEXIST [DRY-RUN] would apply 2 tag(s): Environment=Production  Owner=OIT-Cloud
[OK ] AWS   tagger-test-ec2-1         [DRY-RUN] would apply 4 tag(s): Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AWS   i-02f85514dc2a56857       [DRY-RUN] would apply 3 tag(s): Environment=Staging  Owner=OIT-Cloud  Team=Research
[OK ] AWS   i-0569ff04a074f4780       [DRY-RUN] would apply 4 tag(s): Environment=Dev  CostCenter=456  Department=Engineering  Team=Platform

Done — 7 succeeded, 0 failed
```

**Result:** PASS — all rows parsed and previewed correctly including the bad VM name row.

---

## Live Run Results

```
Loaded 7 VM(s) from samples/test_run.csv

[OK ] AZURE tagger-test-vm1           Applied 4 tag(s): Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AZURE tagger-test-vm2           Applied 2 tag(s): Environment=Staging  Owner=OIT-Cloud
[OK ] AZURE tagger-test-vm3           Applied 3 tag(s): Environment=Dev  Owner=OIT-Cloud  CostCenter=456
[ERR] AZURE tagger-test-vm-DOESNOTEXIST  (ResourceNotFound) The Resource ... was not found.
[OK ] AWS   tagger-test-ec2-1         Applied 4 tag(s) to ['i-0f4b9dddc1b2204d2']: Environment=Production  Owner=OIT-Cloud  CostCenter=123  Project=VMTaggerTest
[OK ] AWS   i-02f85514dc2a56857       Applied 3 tag(s) to ['i-02f85514dc2a56857']: Environment=Staging  Owner=OIT-Cloud  Team=Research
[OK ] AWS   i-0569ff04a074f4780       Applied 4 tag(s) to ['i-0569ff04a074f4780']: Environment=Dev  CostCenter=456  Department=Engineering  Team=Platform

Done — 6 succeeded, 1 failed
```

**Result:** PASS — 6/6 real VMs tagged, 1 expected error on the non-existent VM.

---

## Tag Verification

### Azure (confirmed via `az vm show --query tags`)

| VM | Tags Applied |
|----|-------------|
| tagger-test-vm1 | Environment=Production, Owner=OIT-Cloud, CostCenter=123, Project=VMTaggerTest |
| tagger-test-vm2 | Environment=Staging, Owner=OIT-Cloud |
| tagger-test-vm3 | Environment=Dev, Owner=OIT-Cloud, CostCenter=456 |

### AWS (confirmed via `aws ec2 describe-instances`)

| Instance ID | Tags Applied |
|-------------|-------------|
| i-0f4b9dddc1b2204d2 | Environment=Production, Owner=OIT-Cloud, CostCenter=123, Project=VMTaggerTest, Name=tagger-test-ec2-1 (pre-existing) |
| i-02f85514dc2a56857 | Environment=Staging, Owner=OIT-Cloud, Team=Research, Name=tagger-test-ec2-2 (pre-existing) |
| i-0569ff04a074f4780 | Environment=Dev, CostCenter=456, Department=Engineering, Team=Platform, Name=tagger-test-ec2-3 (pre-existing) |

**Pre-existing `Name` tags were preserved** — merge behavior confirmed.

---

## Issues Found & Fixed

| # | Issue | Fix |
|---|-------|-----|
| 1 | `AWS_PROFILE=claude-bedrock` set in shell env caused boto3 to use an expired SSO token instead of static credentials | Clear `AWS_PROFILE` at process startup when no `--aws-profile` is specified. Set `AWS_PROFILE_KEEP=1` to suppress. |

---

## Summary

| Scenario | Result |
|----------|--------|
| Azure — tag by VM name (multiple tags) | PASS |
| Azure — tag by VM name (few tags) | PASS |
| Azure — non-existent VM error handling | PASS (clean error message) |
| AWS — tag by Name tag | PASS |
| AWS — tag by instance ID | PASS |
| AWS — preserve pre-existing tags | PASS |
| Dry-run preview for all scenarios | PASS |
