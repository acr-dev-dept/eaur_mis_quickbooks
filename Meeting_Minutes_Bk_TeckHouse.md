![](Aspose.Words.53c3d3bf-7850-4bdf-922b-2bf1dab780d5.001.png)

**Meeting Minutes – Urubuto Pay Integration Discussion** 

**Date:** August 13, 2025 

` `**Start Time:** 3:40 PM 

` `**End Time:** 4:05 PM 

` `**Location:** BK Tech House Headquarters – KN 30 St, Kigali, Rwanda 

**Attendees:** 

- Bruce Karagire ,Sr. Manager, Business and Customer Experience, BK Tech House. 
- Gratien Tuyishimire, Software Engineer,BK Tech House 
- Alex Rugema, Software engineer, ACR-Online Accounting Services Ltd  
- Patrick Muvunyi, Software engineer, ACR-Online Accounting Services Ltd 
### **Agenda** 
- Discuss Urubuto Pay’s current payment process and integration possibilities for EAUR MIS–QuickBooks project 
### **Meeting Notes** 
1. **Introduction** 
- The meeting began with introductions, led by Bruce Karagire from BK Tech House. 
2. **Current Urubuto Pay Payment Process** 
- Students currently pay via USSD using the code **\*775#**, then: 
  - Enter Merchant Code( Unique identifier for EAUR) 
  - Enter Student Registration Number 
  - Select services offered (linked to the bank accounts specified by the client, EAUR in this case) 
- Funds can be deposited into different bank accounts or a single account, depending on the client’s requirements. 
- Urubuto Pay also supports debit/credit card payments, though these incur merchant charges. 
3. **Proposed Integration Workflow** 
- The ACR team presented the planned workflow to simplify the student payment process: 
- Students initiate payment directly from the MIS. 
- An invoice is generated with a unique reference number. 
- The student enters the phone number they will use to pay. 
- The system triggers a USSD payment prompt (popup) on that phone via Urubuto Pay’s API. 
- The student completes the payment through the popup, without navigating the traditional USSD menu. 
- For those who do not wish to complete the transaction right away, they will dial the USSD, and enter the reference number found in MIS. 
4. **Agreements & Technical Points** 
- Urubuto Pay will share **API documentation**. 
- Urubuto Pay will provide a **transaction confirmation endpoint** for incomplete or delayed payments. This endpoint will be queried by the microservice in case of timeouts or delays to confirm the transaction details if it went through or not. 
- Urubuto Pay will send **payment notifications** to the callback endpoint provided by ACR. 
- Metadata can be embedded into the reference number to include additional relevant information. 
- Urubuto Pay will update their process logic to support payment via reference number. 
- USSD interaction will be optimized using the provided API. 
- Uruboto Pay designated Mr.Tuyishimire for any technical inquiries during the integration process. 

**Action Items:** 



|**Action Item** |**Responsible Party** |**Due Date** |
| - | :- | - |
|Share API documentation |Urubuto Pay |August 13, 2025 |
|Provide transaction confirmation endpoint |Urubuto Pay |August 20, 2025 |
|Develop and share callback endpoint for payment notifications |ACR Team |August 20, 2025 |
|Share Sandbox credentials |Urubuto Pay |August 13, 2025 |
|Integrate Urubuto Pay with the microservice |ACR Team |August 28, 2025 |

**Adjournment:** 

` `The meeting concluded at 4:05 PM with both teams aligned on the integration approach and next steps. 

**Minutes Prepared By:** 

` `Alex Rugema 

` `Software Engineer 

` `ACR-Online Accounting Services Ltd. 
