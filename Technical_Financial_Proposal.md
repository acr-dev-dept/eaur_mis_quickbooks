---
title: "[]{#_heading=h.4p3yp3i1gsap .anchor}Real-Time MIS-QuickBooks
  Integration & System Modernization Project "
---

> **Prepared By:**
>
> **ACR-ONLINE ACCOUNTING SERVICES LTD:** *a Rwandan incorporated
> professional accounting firm under the Rwandan company act. We offer a
> wide range of outsourced accounting, bookkeeping, tax, and auditing
> services to small and medium businesses. We are the first and most
> affordable accounting and consulting firm based in Rwanda.*
>
> **Prepared For:**
>
> **East African University Rwanda (EAUR) Management Team**
>
> **Date**: 02-June-2025

**Table of Contents**

[1. Executive Summary 3](#_heading=)

> [Project Scope & Impact 3](#_heading=)
>
> [Business Value Delivered 3](#_heading=)

[2. Strategic Objectives & Business Goals 4](#_heading=)

> [Primary Objectives 4](#_heading=)
>
> [Technical Objectives 4](#_heading=)
>
> [Business Impact Goals 4](#_heading=)

[3. System Overview and Current Challenges 5](#_heading=)

> [3.1 Existing Setup 5](#_heading=)
>
> [3.2 Identified Issues 5](#_heading=)

[4. Proposed System Design 6](#_heading=)

[5. Technical Implementation Plan 7](#_heading=)

> [5.1 Schema Refactoring 7](#_heading=)
>
> [Add Reference and Slip Numbers 7](#add-reference-and-slip-numbers)
>
> [5.2 Flask Microservice Responsibilities 8](#_heading=)
>
> [5.3 USSD Workflow Overhaul 8](#_heading=)

[8. Testing Plan 9](#_heading=)

[7. Financial Proposal (2-Month Delivery) 9](#_heading=)

> [7.1 Detailed Cost Breakdown 9](#_heading=)
>
> [7.2 Return on Investment Analysis 10](#_heading=)

[8. Implementation Timeline (8 Weeks) 10](#_heading=)

> [Phase 1: Foundation & Planning (Weeks 1-2) 10](#_heading=)
>
> [Week 1: Requirements & Design 10](#_heading=)
>
> [Week 2: Architecture & Setup 10](#_heading=)
>
> [Phase 2: Core Development (Weeks 3-5) 11](#_heading=)
>
> [Week 3: Database & Core Services 11](#_heading=)
>
> [Week 4: Integration Development 11](#_heading=)
>
> [Week 5: Data Migration & Sync 11](#_heading=)
>
> [Phase 3: Testing & Refinement (Weeks 6-7) 11](#_heading=)
>
> [Week 6: Comprehensive Testing 11](#_heading=)
>
> [Week 7: User Acceptance & Training 11](#_heading=)
>
> [Phase 4: Deployment & Support (Week 8) 12](#_heading=)
>
> [Week 8: Go-Live & Handover 12](#_heading=)

[9. Why Choose ACR for This Project? 12](#_heading=)

> [9.1 Technical Excellence 12](#_heading=)
>
> [9.2 Project Management Excellence 12](#_heading=)
>
> [9.3 Business Understanding 12](#_heading=)

[10. Project Deliverables 13](#_heading=)

> [10.1 Technical Deliverables 13](#_heading=)
>
> [10.2 Documentation & Training 13](#_heading=)
>
> [10.3 Support & Maintenance 13](#_heading=)

# Executive Summary

> East African University Rwanda requires a comprehensive digital
> transformation of its financial management system to achieve real-time
> synchronization between its Management Information System (MIS) and
> QuickBooks Online. This is not merely a simple integration project,
> but a complete system modernization that addresses critical
> operational challenges and establishes a foundation for scalable
> growth.

## Project Scope & Impact

> This project encompasses:

-   **Complete database architecture redesign** to support real-time
    > operations

-   **Advanced USSD payment system integration** with customized
    > reference number generation

-   **Automated student lifecycle management** from application to
    > graduation

-   **Real-time financial synchronization** eliminating manual data
    > entry

-   **Comprehensive reporting system** for management decision-making

-   **Fraud prevention mechanisms** through advanced reference number
    > validation

## Business Value Delivered

-   **Operational Efficiency**: Eliminate 40+ hours/week of manual data
    > entry

-   **Financial Accuracy**: 100% synchronization between MIS and
    > QuickBooks

-   **Revenue Protection**: Advanced fraud detection and duplicate
    > payment prevention

-   **Regulatory Compliance**: Automated audit trails and financial
    > reporting

-   **Scalability**: System capable of handling 10x current student
    > volume

# Strategic Objectives & Business Goals

## Primary Objectives

-   **Real-Time Financial Synchronization**: Achieve instant,
    > bidirectional sync between MIS and QuickBooks for all financial
    > transactions

-   **Complete Student Lifecycle Management**: Automate financial
    > tracking from application submission to graduation

-   **Advanced Payment Processing**: Implement sophisticated USSD
    > integration with fraud prevention mechanisms

-   **Operational Excellence**: Eliminate manual data entry and reduce
    > processing errors to zero

-   **Regulatory Compliance**: Ensure full audit trail and financial
    > reporting compliance

## Technical Objectives

-   **Database Architecture Modernization**: Complete restructuring for
    > real-time operations and scalability

-   **Microservices Implementation**: Deploy enterprise-grade
    > Flask-based integration layer

-   **Payment Gateway Integration**: Custom USSD integration with School
    > Gear and Urubuto Pay

-   **Security Enhancement**: Implement advanced fraud detection and
    > duplicate payment prevention

-   **Performance Optimization**: Ensure system can handle 10x current
    > transaction volume

## Business Impact Goals

> ![](media/image3.png){width="5.2083333333333336e-2in"
> height="5.2081146106736656e-2in"} **Cost Reduction**: Eliminate 40+
> hours/week of manual financial data entry
>
> ![](media/image1.png){width="5.2083333333333336e-2in"
> height="5.2081146106736656e-2in"} **Revenue Protection**: Prevent
> duplicate payments and fraudulent transactions
>
> ![](media/image1.png){width="5.2083333333333336e-2in"
> height="5.2081146106736656e-2in"} **Decision Making**: Provide
> real-time financial dashboards for management via Quickbooks reporting
>
> ![](media/image2.png){width="5.2083333333333336e-2in"
> height="5.2081146106736656e-2in"} **Student Experience**: Streamline
> payment processes with instant confirmation
>
> ![](media/image1.png){width="5.2083333333333336e-2in"
> height="5.2081146106736656e-2in"} **Audit Readiness**: Maintain
> complete, automated audit trails for all transactions

3.  # System Overview and Current Challenges

    1.  ## Existing Setup

-   PHP-based MIS hosted on a single DigitalOcean droplet.

-   MySQL database co-hosted on the same server.

-   QuickBooks is not integrated with MIS.

-   USSD used for student payments.

    1.  ## Identified Issues

From the technical meeting we had, we identified a few issues that have
to be amended so as to enable the auto synchronization. This is not an
exhaustive list, as all the issues cannot be identified in a single
meeting. We expect to find more during the implementation phase as we
continue to interact with the system.

+-------------------------+--------------------------------------------+
| > **Issue**             | > **Description**                          |
+=========================+============================================+
| No invoice-payment link | The payments table lacks a connection to   |
|                         | Invoices. This is problematic because the  |
|                         | Finance department is not able to map a    |
|                         | payment with a specific invoice.           |
+-------------------------+--------------------------------------------+
| Slow Queries            | This is most likely caused by the app and  |
|                         | the database running on the same server    |
|                         | competing for cpu resources.               |
+-------------------------+--------------------------------------------+
| Hardcoded Scholarships  | EAUR scholarship values are based on       |
|                         | memorised table rows. Currently there's no |
|                         | column specifying the exact values of the  |
|                         | percentage.                                |
+-------------------------+--------------------------------------------+
| Duplicated Fee          | Fee category versioning is handled by      |
| categories              | creating new rows and deactivating the old |
|                         | ones.                                      |
+-------------------------+--------------------------------------------+
| USSD Payment Errors     | Students frequently select wrong fees when |
|                         | paying.                                    |
+-------------------------+--------------------------------------------+
| No Data Sync in         | All financial data is entered manually     |
| Quickbooks              | into QB                                    |
+-------------------------+--------------------------------------------+
| Fee structure lacks     | Prices are stored inconsistently with      |
| normalisation           | active/inactive flags.                     |
+-------------------------+--------------------------------------------+

4.  # Proposed System Design

    1.  **Architecture**

![](media/image4.png){width="7.870662729658792in"
height="7.243290682414698in"}

5.  # Technical Implementation Plan

    1.  ## Schema Refactoring

The table below outlines what we will change in the database schema to
achieve automatic synchronization of the current system with Quickbooks
online. Please note that additional schema changes might be applied as
we explore the MIS more.

+--------------+----------------+--------------------------------------+
| **Action**   | **Current      | **Proposed change**                  |
|              | State**        |                                      |
+==============+================+======================================+
| Link         | No Link        | The Payments table needs to be       |
| Payments to  |                | altered to reference the invoice_id. |
| Invoices     |                |                                      |
+--------------+----------------+--------------------------------------+
| Normalize    | Based on Row   | We need to create a separate table   |
| Scholarships | Index          | that tracks scholarships and their   |
|              |                | percentages                          |
+--------------+----------------+--------------------------------------+
| Normalize    | Duplicate rows | We need to have a table for the fee  |
| Fee          | with active    | category containing columns such as  |
| categories   | and inactive   | the name, and the id of the          |
|              | status         | category.\                           |
|              |                | We would then have a separate table  |
|              |                | handling the fees of each category   |
|              |                | that we can call fee_prices. It      |
|              |                | would contain columns such as id,    |
|              |                | fee_category_id, price,              |
|              |                | effective_date, end_date.\           |
|              |                | \                                    |
|              |                | This would keep the fee categories   |
|              |                | intact, what would keep changing is  |
|              |                | the price of the category and        |
|              |                | effective date. So depending on the  |
|              |                | date of the invoice generation, we   |
|              |                | would map the fee of the category    |
|              |                | accordingly.                         |
+--------------+----------------+--------------------------------------+
| #### Add Re  | Not applicable | When a student pays, we need to sync |
| ference and  |                | with Quickbooks.The data containing  |
| Slip Numbers |                | the slip numbers are generated by    |
|              |                | School Gear and Urubuto Pay          |
+--------------+----------------+--------------------------------------+
| Introduce    | Not applicable | This table will show if an           |
| Audit Logs   |                | invoice/payment or some other        |
| Table        |                | information that might deem          |
|              |                | necessary for syncing with QB if it  |
|              |                | has been synched, and at what time.  |
+--------------+----------------+--------------------------------------+

## Flask Microservice Responsibilities

We intend to use a microservice architecture. The Microservice will be
running on separate servers communicating with MIS as well as listening
to the Database for any changes to specific tables.

  -----------------------------------------------------------------------
  **Function**                  **Description**
  ----------------------------- -----------------------------------------
  Invoice Sync                  Listen for new/updated invoices, apply
                                scholarship, push to QB

  QB Payment Sync               Ensure payment matches involve, synch to
                                QB

  QB Auth                       Manage OAuth2 tokens

  Securely Caching              Redis for reference data

  Error Logging                 Log failures in **sync_logs** table

  Manuel Triggers               Admin panel to re-sync or validate
                                records
  -----------------------------------------------------------------------

## USSD Workflow Overhaul

**Proposed Flow**:

1.  Student logs into MIS → makes a payment request

2.  MIS generates invoice with a unique **reference_number**

3.  Student pays via USSD or interface using this reference number

4.  Flask service fetches payment → validates & syncs to QB

5.  Reference number ensures exact fee category is credited

```{=html}
<!-- -->
```
6.  Reporting

All the reports will be obtained from Quickbooks. Since Quickbooks will
now have accurate financial data, the finance department will be able to
generate any report of their choosing.

7.  **Security**

-   Encrypted OAuth2 tokens for QuickBooks.

-   Flask microservice protected via internal API key.

-   MIS will only interact with Flask via internal secure requests.

-   Audit logs for every sync.

# Testing Plan

-   Sync mock invoices & payments to QB sandbox.

-   Validate field mapping & data consistency.

-   Test edge cases: scholarships, concessions, multiple payments.

-   Stress test under high USSD activity.

7.  # Financial Proposal (2-Month Delivery)

    1.  ## Detailed Cost Breakdown

  ---------------------------------------------------------------------------------------
  **Phase**       **Component**              **Hours**   **Rate(RWF)**   **Total(RWF)**
  --------------- -------------------------- ----------- --------------- ----------------
  **Phase 1**     Requirement & Architecture 20          20,000          400,000
                  Design                                                 

                  Environment Setup &        20          20,000          400,000
                  Configuration                                          

  **Phase 2**     Flask Microservices        80          20,000          1,600,000
                  Development                                            

                  QuickBooks API Integration 80          20,000          1,600,000

                  Database Schema            20          20,000          400,000
                  Modernization                                          

                  USSD Integration & Payment 55          20,000          1,100,000
                  Gateway                                                

  **Phase 3**     2025 Data Migration        25          20,000          500,000

                  Comprehensive Testing & QA 20          20,000          400,000

                  User Training &            20          20,000          400,000
                  Documentation                                          

  **Phase 4**     Deployment & Go-Live       35          20,000          700,000
                  Support                                                

                  Post-Deployment Support (4 16          20,000          320,000
                  weeks)                                                 

  **Total(Tax                                                            **7,820,000**
  Exclussive)**                                                          

  **Grand                                                                **9,227,600**
  Total(Tax                                                              
  Inclusive)**                                                           
  ---------------------------------------------------------------------------------------

## Return on Investment Analysis

  ---------------------------------------------------------------------------------
  **Cost Area**             **Total Hours/week**   **Rate(RWF)**   **Total Annual
                                                                   Cost**
  ------------------------- ---------------------- --------------- ----------------
  Manual Data Entry         40                     3,000           6,240,000

  Error Correction          10                     3,000           1,560,000

  Duplicate Payments        5                      3,000           780,000

  Audit Prep Overhead       10                     20,000          10,400,000

  **Total Annual Cost**                                            **18,980,000**
  ---------------------------------------------------------------------------------

  ---------- --------------- -------------- ------------------ ------------ ----------
  **Year**   **Annual        **Cumulative   **Investment Cost  **Net        **ROI %**
             Savings (RWF)** Savings**      (One-time)**       Return**     

  1          18,980,000      18,980,000     9,227,600          9,752,400    106

  2          18,980,000      37,960,000     9,227,600          28,732,400   311

  3          18,980,000      56,940,000     9,227,600          47,712,400   517

  4          18,980,000      75,920,000     9,227,600          66,692,400   723
  ---------- --------------- -------------- ------------------ ------------ ----------

# Implementation Timeline (8 Weeks)

## Phase 1: Foundation & Planning (Weeks 1-2)

### Week 1: Requirements & Design

-   Detailed stakeholder requirement sessions

-   Database schema design and approval

-   QuickBooks environment setup and configuration

-   Development environment preparation

### Week 2: Architecture & Setup

-   Flask microservice architecture implementation

-   API endpoint specifications and documentation

-   Database migration scripts preparation

-   Testing environment configuration

## 

## Phase 2: Core Development (Weeks 3-5)

### Week 3: Database & Core Services

-   Complete schema refactoring implementation

-   Core Flask microservice development

-   Basic QuickBooks API integration

-   Reference number system foundation

### Week 4: Integration Development

-   Complete QuickBooks API integration

-   USSD workflow implementation

-   Payment gateway API integration

-   Advanced error handling and logging

### Week 5: Data Migration & Sync

-   Student master data import (all students)

-   2025 financial data migration (invoices & payments)

-   Real-time sync implementation

-   Initial testing and validation

## Phase 3: Testing & Refinement (Weeks 6-7)

### Week 6: Comprehensive Testing

-   QuickBooks sandbox environment testing

-   USSD payment flow testing

-   Data validation and reconciliation

-   Performance optimization and tuning

### Week 7: User Acceptance & Training

-   User acceptance testing with finance team

-   Comprehensive staff training sessions

-   Documentation completion and handover

-   Final system adjustments

## 

## 

## Phase 4: Deployment & Support (Week 8)

### Week 8: Go-Live & Handover

-   Production deployment and monitoring

-   Live data validation and verification

-   Post-deployment support and monitoring

-   Project completion and documentation handover

9.  # Why Choose ACR for This Project?

    1.  ## Technical Excellence

-   **Proven Experience**: Successfully Integrated enterprise grade
    > systems with Irembopay, Quickbooks Online, Biometric devices,
    > Facial Recognition API, Amazon S3 storage object Integration for
    > document management and storage.

-   **Modern Architecture**: Expertise in microservices and cloud
    > technologies

-   **Quality Assurance**: Comprehensive testing methodologies

-   **Future-Ready Solutions**: Scalable, maintainable system design

    1.  ## Project Management Excellence

```{=html}
<!-- -->
```
-   **Structured Approach**: Clear phases, milestones, and deliverables

-   **Risk Management**: Proactive identification and mitigation

-   **Communication**: Regular updates and stakeholder engagement

-   **Support**: Extended post-deployment support included

    1.  ## Business Understanding

```{=html}
<!-- -->
```
-   **Sector Expertise**: Deep understanding of business operations

-   **Financial Systems Knowledge**: Extensive QuickBooks integration
    > experience

-   **Local Market Understanding**: Rwanda-specific requirements and
    > regulations

-   **Long-term Partnership**: Committed to ongoing success and growth

10. # Project Deliverables

    1.  ## Technical Deliverables

-   **Flask Microservice**: Complete source code with deployment scripts

-   **Database Updates**: Schema migration scripts and documentation

-   **QuickBooks Integration**: Live/sandbox integration with full
    > functionality

-   **USSD Payment System**: Reference number generation and validation

-   **Real-Time Sync**: Automated synchronization between MIS and
    > QuickBooks

    1.  ## Documentation & Training

```{=html}
<!-- -->
```
-   **Technical Documentation**: Complete system architecture and API
    > documentation

-   **User Manuals**: Step-by-step guides for all system functions

-   **Training Sessions**: Comprehensive staff training (2 sessions)

-   **Support Materials**: Troubleshooting guides and best practices

    1.  ## Support & Maintenance

```{=html}
<!-- -->
```
-   **Go-Live Support**: 1 week intensive support during deployment

-   **After Sales Support**: 3 months post-deployment support included

-   **Performance Monitoring**: System health monitoring and reporting

-   **Future Enhancements**: Roadmap for additional features and
    > improvements
