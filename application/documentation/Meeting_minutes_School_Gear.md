![](Aspose.Words.116d9ff1-d57a-4203-b8b1-5258cae171f5.001.png)

**Date:** August 13, 2025 **Start Time:** 11:00 AM **Location:** Virtual **Attendees:** 

- Alex Rugema, Software engineer, ACR-Online Accounting Services Ltd  
- Patrick Muvunyi, Software engineer, ACR-Online Accounting Services Ltd 
- Derick Gusenga, Devops Engineer, Ion Plus technology Ltd 
- Mechac Nzirayukuri, CEO, Ion Plus Technology Ltd 

**Agenda:** School Gear integration with Flask microservice for MIS–QuickBooks project 
### **Meeting Notes** 
1. **Project Context** 
- The ACR team presented the overall project concept and explained the necessity for the new changes. 
- The flow of the reference number was discussed, including its handling at the bank and via USSD. 
2. **Technical Requirements & Agreements** 
- **Invoice Details Endpoint**:  ACR will provide an endpoint that returns the details of an invoice given a reference number.This will include amount due, student details, and other necessary metadata for payment processing. 
- **Student Invoices Endpoint**:  ACR will provide an endpoint to return all invoices linked to a student, using the student registration number as input. 
- **Payment Callback URL**: 

  ` `ACR will develop a callback endpoint for School Gear to post payment results. 

  ` `The microservice will update the MIS database accordingly upon receiving the callback. 

- **Reversal Endpoint**: 

  ` `School Gear requested an endpoint for payment reversals in case of disputes or reimbursements. 

- **USSD Payment Prompt**: 

  ` `School Gear will provide the endpoint that triggers a payment prompt (popup) on the student’s phone. 

  ` `The system should allow payment from any phone number of the student’s choice.** 

**Action Items:** 



|**Action** |**Responsible Party** |**Due Date** |
| - | - | - |
|Provide invoice details endpoint |ACR Team |August 28, 2025 |
|Provide student invoices endpoint |ACR Team |August 28, 2025 |
|Develop payment callback URL |ACR Team |August 28, 2025 |
|Develop reversal endpoint |ACR Team |August 28, 2025 |
|Share  payment initiation endpoint |School Gear |August 28, 2025 |

**Adjournment:** 

The meeting concluded at 11:40 AM, with Alex Rugema expressing appreciation for the School Gear team’s collaboration and valuable insights. 

**Minutes Prepared By:** 

Alex Rugema 

Software Engineer 

ACR-Online Accounting Services Ltd.
