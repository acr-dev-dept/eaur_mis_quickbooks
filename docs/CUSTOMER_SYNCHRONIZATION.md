# Customer Synchronization Guide

## Overview

The EAUR MIS-QuickBooks Integration includes a comprehensive customer synchronization system that automates the transfer of applicants and students from the MIS database to QuickBooks Online as customers. This system ensures complete data coverage, proper categorization, and maintains data integrity across both systems.

## Features

### ==YES==**Dual Customer Types**
- **Applicants**: From `tbl_online_application` → QuickBooks Customers (`CustomerType: "Applicant"`)
- **Students**: From `tbl_personal_ug` → QuickBooks Customers (`CustomerType: "Student"`)
- **Separate Records**: Same person can exist as both applicant and student with different identifiers

### ==YES==**Comprehensive Data Mapping**
- **Real Names**: Display names use actual names (e.g., "John Doe", not "APP-John Doe")
- **Rich Custom Fields**: Campus, program, intake, gender, national ID, etc.
- **Data Enrichment**: IDs converted to readable names with fallback handling
- **Complete Coverage**: ALL records included, even with missing data

### ==YES==**Robust Synchronization**
- **Batch Processing**: Configurable batch sizes to respect API limits
- **Status Tracking**: Track sync status for each customer
- **Error Handling**: Graceful handling of missing data and API errors
- **Progress Monitoring**: Real-time progress tracking and reporting

## Architecture

### Database Schema Enhancements

Both customer tables now include sync tracking fields:

```sql
-- Added to tbl_online_application
QuickBk_Status    INT DEFAULT 0           -- 0=not synced, 1=synced, 2=failed, 3=in progress
pushed_by         VARCHAR(200) DEFAULT 'System Auto Push'
pushed_date       DATETIME

-- Added to tbl_personal_ug  
QuickBk_Status    INT DEFAULT 0           -- 0=not synced, 1=synced, 2=failed, 3=in progress
pushed_by         VARCHAR(200) DEFAULT 'System Auto Push'
pushed_date       DATETIME
```

### Service Layer

**CustomerSyncService** (`application/services/customer_sync.py`)
- Applicant and student synchronization logic
- Data mapping and enrichment with fallbacks
- QuickBooks customer creation and management
- Status tracking and audit logging

### API Layer

**Customer Sync API** (`application/api/v1/customer_sync.py`)
- RESTful endpoints for customer synchronization
- Separate endpoints for applicants and students
- Progress monitoring and status reporting

## Data Mapping

### Applicant Data Mapping

| MIS Field (`tbl_online_application`) | QuickBooks Field | Custom Field Name | Notes |
|-------------------------------------|------------------|-------------------|-------|
| `first_name + family_name` | `DisplayName` | - | Real name only |
| `first_name` | `GivenName` | - | First name |
| `family_name` | `FamilyName` | - | Last name |
| `phone1` | `PrimaryPhone` | - | Contact number |
| `email1` | `PrimaryEmailAddr` | - | Email address |
| - | `CustomField` | `CustomerType` | **"Applicant"** |
| `appl_Id` | `CustomField` | `ApplicationID` | Unique applicant ID |
| `tracking_id` | `CustomField` | `TrackingID` | Application tracking ID |
| `sex` | `CustomField` | `Gender` | Gender information |
| `country_of_birth` | `CustomField` | `BirthCountry` | Birth country |
| `nation_Id_passPort_no` | `CustomField` | `NationalID` | ID/Passport number |
| `camp_id` → enriched | `CustomField` | `Campus` | Campus name |
| `intake_id` → enriched | `CustomField` | `Intake` | Intake details |
| `opt_1` → enriched | `CustomField` | `Program` | Program name |
| `prg_mode_id` → enriched | `CustomField` | `ProgramMode` | Program mode |

### Student Data Mapping

| MIS Field (`tbl_personal_ug`) | QuickBooks Field | Custom Field Name | Notes |
|------------------------------|------------------|-------------------|-------|
| `fname + lname` | `DisplayName` | - | Real name only |
| `fname` | `GivenName` | - | First name |
| `lname` | `FamilyName` | - | Last name |
| `phone1` | `PrimaryPhone` | - | Contact number |
| `email1` | `PrimaryEmailAddr` | - | Email address |
| - | `CustomField` | `CustomerType` | **"Student"** |
| `reg_no` | `CustomField` | `RegNo` | Registration number |
| `sex` | `CustomField` | `Gender` | Gender information |
| `national_id` | `CustomField` | `NationalID` | National ID |
| Level from registration | `CustomField` | `Level` | Academic level |
| Campus from registration | `CustomField` | `Campus` | Campus name |
| Intake from registration | `CustomField` | `Intake` | Intake details |
| Program from registration | `CustomField` | `Program` | Program name |
| `prg_type` | `CustomField` | `ProgramType` | Program type |

## Usage Guide

### 1. Prerequisites

Ensure the following before starting synchronization:

1. **QuickBooks Authentication**: QuickBooks must be connected
2. **Database Access**: MIS database connection configured
3. **Sync Fields**: New tracking fields added to tables (handled automatically)

```bash
# Check system status
curl http://localhost:5000/api/v1/sync/customers/status
```

### 2. Analysis Phase

Analyze your customer synchronization requirements:

#### Via API:
```bash
curl http://localhost:5000/api/v1/sync/customers/analyze
```

#### Via Command Line:
```bash
python3 tools/sync_customers.py analyze
```

**Sample Output:**
```
📊 Customer Synchronization Statistics:

👥 APPLICANTS:
   Total Applicants: 850
   ==YES==Already Synced: 0
   ⏳ Not Synced: 850
   ❌ Failed: 0
   🔄 In Progress: 0
   📈 Progress: 0.0%

🎓 STUDENTS:
   Total Students: 1,200
   ==YES==Already Synced: 0
   ⏳ Not Synced: 1,200
   ❌ Failed: 0
   🔄 In Progress: 0
   📈 Progress: 0.0%

🌟 OVERALL:
   Total Customers: 2,050
   ==YES==Total Synced: 0
   ⏳ Total Not Synced: 2,050
   📈 Overall Progress: 0.0%
```

### 3. Preview Phase

Preview customers that will be synchronized:

#### Preview Applicants:
```bash
# Via API
curl "http://localhost:5000/api/v1/sync/customers/preview/applicants?limit=10"

# Via CLI
python3 tools/sync_customers.py preview-applicants --limit 10
```

#### Preview Students:
```bash
# Via API
curl "http://localhost:5000/api/v1/sync/customers/preview/students?limit=10"

# Via CLI
python3 tools/sync_customers.py preview-students --limit 10
```

### 4. Synchronization Options

#### Option A: Sync Applicants Only

**API:**
```bash
curl -X POST http://localhost:5000/api/v1/sync/customers/applicants \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 50}'
```

**Command Line:**
```bash
python3 tools/sync_customers.py applicants --batch-size 50
```

#### Option B: Sync Students Only

**API:**
```bash
curl -X POST http://localhost:5000/api/v1/sync/customers/students \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 50}'
```

**Command Line:**
```bash
python3 tools/sync_customers.py students --batch-size 50
```

#### Option C: Sync All Customers

**API:**
```bash
curl -X POST http://localhost:5000/api/v1/sync/customers/all \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 50,
    "sync_applicants": true,
    "sync_students": true
  }'
```

### 5. Monitoring Progress

Monitor synchronization progress:

#### Via API:
```bash
curl http://localhost:5000/api/v1/sync/customers/status
```

#### Via Command Line:
```bash
python3 tools/sync_customers.py status
```

## API Reference

### GET /api/v1/sync/customers/analyze
Analyze customer synchronization requirements.

**Response:**
```json
{
  "success": true,
  "data": {
    "applicants": {
      "total": 850,
      "not_synced": 850,
      "synced": 0,
      "failed": 0,
      "in_progress": 0
    },
    "students": {
      "total": 1200,
      "not_synced": 1200,
      "synced": 0,
      "failed": 0,
      "in_progress": 0
    },
    "overall": {
      "total_customers": 2050,
      "total_not_synced": 2050,
      "total_synced": 0,
      "total_failed": 0
    }
  }
}
```

### GET /api/v1/sync/customers/preview/applicants
Preview unsynchronized applicants.

**Parameters:**
- `limit` (optional): Number of applicants to return (default: 10, max: 100)
- `offset` (optional): Number of applicants to skip (default: 0)

### GET /api/v1/sync/customers/preview/students
Preview unsynchronized students.

**Parameters:**
- `limit` (optional): Number of students to return (default: 10, max: 100)
- `offset` (optional): Number of students to skip (default: 0)

### POST /api/v1/sync/customers/applicants
Synchronize applicants to QuickBooks customers.

**Request Body:**
```json
{
  "batch_size": 50
}
```

### POST /api/v1/sync/customers/students
Synchronize students to QuickBooks customers.

**Request Body:**
```json
{
  "batch_size": 50
}
```

### POST /api/v1/sync/customers/all
Synchronize all customers (applicants and students).

**Request Body:**
```json
{
  "batch_size": 50,
  "sync_applicants": true,
  "sync_students": true
}
```

### GET /api/v1/sync/customers/status
Get current customer synchronization status.

## Command Line Tools

### Available Commands

```bash
# Analyze requirements
python3 tools/sync_customers.py analyze

# Preview data
python3 tools/sync_customers.py preview-applicants --limit 10
python3 tools/sync_customers.py preview-students --limit 10

# Synchronize customers
python3 tools/sync_customers.py applicants --batch-size 50
python3 tools/sync_customers.py students --batch-size 50

# Check status
python3 tools/sync_customers.py status
```

## Data Enrichment & Fallback Strategy

### Enrichment Process

The system enriches ID fields with readable names:

1. **Campus ID** → Campus full name or short name
2. **Intake ID** → Intake name or details  
3. **Program ID** → Program full name or short name
4. **Level ID** → Level full name or short name

### Fallback Strategy

When enrichment fails or data is missing:

1. **First Priority**: Use enriched readable name
2. **Second Priority**: Use the ID value as string
3. **Third Priority**: Use empty string for missing data

**Example:**
```python
# If campus_id = 5 and campus name lookup fails
campus_name = "5"  # Fallback to ID

# If campus_id is None/missing
campus_name = ""   # Empty string
```

This ensures **ALL records are synchronized** regardless of data completeness.

## Best Practices

### 1. **Start with Analysis**
Always run analysis first to understand the scope:
```bash
python3 tools/sync_customers.py analyze
```

### 2. **Preview Before Sync**
Preview a small sample to verify data mapping:
```bash
python3 tools/sync_customers.py preview-applicants --limit 5
```

### 3. **Use Appropriate Batch Sizes**
- **Small batches (10-20)**: For testing and validation
- **Medium batches (50)**: For regular synchronization
- **Large batches (100)**: Only for bulk operations with good connectivity

### 4. **Monitor Progress**
Regularly check synchronization status:
```bash
python3 tools/sync_customers.py status
```

### 5. **Handle Duplicates Properly**
- Same person as applicant and student = Two separate customer records
- Different `CustomerType` custom field distinguishes them
- Use `ApplicationID` for applicants, `RegNo` for students as unique identifiers

## Troubleshooting

### Issue: High Failure Rate
**Symptoms**: Many customers failing to sync
**Solution**:
1. Check QuickBooks connection status
2. Verify data completeness in MIS tables
3. Review error messages in API responses
4. Check QuickBooks custom field limits

### Issue: Missing Enriched Data
**Symptoms**: Campus/Program showing as IDs instead of names
**Solution**:
1. Verify related tables (campus, intake, program) have data
2. Check foreign key relationships
3. Review enrichment method implementations

### Issue: Slow Performance
**Symptoms**: Synchronization taking too long
**Solution**:
1. Reduce batch size
2. Check network connectivity to QuickBooks
3. Monitor API rate limits
4. Run during off-peak hours

## Support

For technical support:
- **Email**: support@acr-online.rw
- **Logs**: Check `logs/app.log` for detailed error information
- **API Errors**: Review QuickBooks audit logs in database
- **Status**: Use status endpoints for real-time monitoring
