# VM Tagger — User Guide

Bulk-tag virtual machines in Azure and AWS from a single CSV or Excel file.
Supports any number of tags per VM, dry-run preview, and both a desktop GUI and command-line interface.

---

## Requirements

- Python 3.10 or later
- Install dependencies:

```bash
pip install -r requirements.txt
```

For Excel (`.xlsx`) support, `openpyxl` is included in `requirements.txt`.
For the desktop GUI on macOS with Homebrew Python, you may also need:

```bash
brew install python-tk
```

---

## Input File Format

Create a CSV or Excel file with the following columns — **one row per VM**:

| Column | Description |
|--------|-------------|
| `cloud` | `azure` or `aws` |
| `subscription_or_account` | Azure subscription ID or AWS account ID |
| `resource_group_or_region` | Azure resource group name or AWS region (e.g. `us-east-1`) |
| `vm_name` | VM name, or EC2 instance ID (`i-0abc1234...`) for AWS |
| `tags` | Semicolon-separated `Key=Value` pairs |

### Tags cell format

All tags for a VM go in one cell, separated by semicolons:

```
Environment=Production;Owner=OIT-Cloud;CostCenter=123
```

### Example CSV

```csv
cloud,subscription_or_account,resource_group_or_region,vm_name,tags
azure,09ee524e-513d-4f21-b758-43277a3b84b2,MY-RESOURCE-GROUP,my-vm-1,Environment=Production;Owner=OIT-Cloud;CostCenter=123
azure,09ee524e-513d-4f21-b758-43277a3b84b2,MY-RESOURCE-GROUP,my-vm-2,Environment=Dev;Owner=OIT-Cloud
aws,390403887416,us-east-1,my-ec2-instance,Environment=Production;Owner=OIT-Cloud
aws,390403887416,us-east-1,i-0abc1234def56789a,Environment=Dev;Team=Research
```

A sample file is included at `samples/vms.csv`.

> **Note:** Existing tags on a VM are preserved. The tool merges new tags on top — it does not wipe what is already there.

---

## Authentication

### Azure

The tool uses `DefaultAzureCredential`, which tries the following in order:

| Method | How to use |
|--------|-----------|
| **Azure CLI** | Run `az login` in your terminal before launching the tool. Easiest for desktop use. |
| **Environment variables** | Set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` for a service principal. |
| **Managed Identity** | If running on an Azure VM with a managed identity, no configuration is needed. |

The identity used must have at least the **Virtual Machine Contributor** role on each subscription listed in the input file.

### AWS

The tool uses the standard boto3 credential chain:

| Method | How to use |
|--------|-----------|
| **AWS CLI profile** | Run `aws configure` to set up `~/.aws/credentials`, then pass `--aws-profile <name>` (or select the profile in the GUI). |
| **Environment variables** | Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. |
| **IAM Instance Profile** | If running on an EC2 instance with an IAM role attached, no configuration is needed. |

The identity used must have the **ec2:CreateTags** and **ec2:DescribeInstances** permissions on the target accounts.

> **Note on AWS_PROFILE:** If your shell has `AWS_PROFILE` set to an SSO profile with expired tokens, the tool automatically clears it at startup so that static credentials in `~/.aws/credentials` take effect. Use `--aws-profile` to explicitly select a named profile instead.

---

## Running the GUI

Launch the desktop window with no arguments:

```bash
python tagger.py
```

![GUI layout]

1. Click **Browse…** to select your CSV or Excel input file.
2. Enter an **AWS profile** name if needed (leave blank to use the default credential chain).
3. Leave **Dry-run** checked to preview what would happen without making any changes.
4. Click **Run**.
5. Review the color-coded log:
   - **Blue** — dry-run preview
   - **Green** — tag applied successfully
   - **Red** — error

When you are satisfied with the dry-run output, uncheck **Dry-run** and click **Run** again to apply.

---

## Running from the Command Line

### Preview (no changes made)

```bash
python tagger.py --input vms.csv --dry-run
```

### Apply tags

```bash
python tagger.py --input vms.csv
```

### Use a named AWS profile

```bash
python tagger.py --input vms.csv --aws-profile bcm-prod
```

### Excel input

```bash
python tagger.py --input vms.xlsx --dry-run
```

### All options

```
usage: tagger.py [-h] [--input FILE] [--dry-run] [--aws-profile PROFILE]

  --input FILE           CSV or Excel input file (omit to launch GUI)
  --dry-run              Preview operations — no changes applied
  --aws-profile PROFILE  AWS credentials profile from ~/.aws/credentials
```

---

## Example Output

```
Loaded 4 VM(s) from vms.csv
DRY-RUN mode — no changes will be applied
AWS profile: bcm-prod

[ERR] AZURE  my-vm-1       azure-identity / azure-mgmt-compute not installed
[DRY] AWS    my-ec2        [DRY-RUN] would apply 3 tag(s) (profile=bcm-prod): Environment=Production  Owner=OIT-Cloud  CostCenter=123
[DRY] AWS    i-0abc1234    [DRY-RUN] would apply 2 tag(s) (profile=bcm-prod): Environment=Dev  Team=Research

Done — 3 succeeded, 1 failed
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `azure-identity / azure-mgmt-compute not installed` | Azure SDK not installed | `pip install -r requirements.txt` |
| `boto3 not installed` | AWS SDK not installed | `pip install -r requirements.txt` |
| `No module named '_tkinter'` | Tkinter native binding missing | `brew install python-tk` |
| `AuthorizationFailed` (Azure) | Identity lacks permission on the subscription | Assign **Virtual Machine Contributor** role |
| `NoCredentialsError` (AWS) | No AWS credentials found | Run `aws configure` or set env vars |
| SSO token errors on AWS even with static keys in `~/.aws/credentials` | `AWS_PROFILE` env var is set and points to an expired SSO profile | The tool clears `AWS_PROFILE` automatically at startup. Set `AWS_PROFILE_KEEP=1` to suppress this behavior and manage the profile yourself. |
| `No instance found with Name=…` (AWS) | VM name not found via Name tag | Use the instance ID (`i-0abc…`) instead |
