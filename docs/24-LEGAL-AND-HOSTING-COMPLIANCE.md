# Legal and Hosting Compliance Roadmap for Amorien

**Amorien** is a private, 1-on-1 AI companion platform featuring video and audio interactions. This roadmap outlines the regulatory, hosting, and privacy considerations necessary to operate safely and legally, particularly given the sensitive nature of intimate or personal conversational AI.

---

## 1. Cloud Provider & Acceptable Use Policies (AUPs)

Hosting an AI companion—especially one that might engage in unrestricted, mature, or romantic themes—requires careful infrastructure selection. Mainstream providers often heavily regulate "NSFW" or sensitive AI interactions.

*   **Hyperscalers (AWS, GCP, Azure):**
    *   *IaaS (Virtual Machines/Compute):* Running your own self-hosted models on standard EC2 instances or GCP Compute Engines is generally permissible as long as the generated content is strictly legal (e.g., no CSAM).
    *   *Managed AI Services (AWS Bedrock, GCP Vertex):* Highly restrictive. They implement strict safety filters and often prohibit generating sexually explicit, highly violent, or unregulated medical/therapeutic advice. **Not recommended for the core conversational model** if you intend to offer an uncensored or highly personalized experience.
*   **Specialized GPU Hosts (RunPod, Lambda Labs, CoreWeave):**
    *   *AUPs:* Generally much more permissive regarding content. They act purely as infrastructure layer providers.
    *   *Recommendation:* **Host the LLM and Voice/Video generation models here.** Use AWS/GCP solely for standard database hosting, user auth, and non-sensitive API routing. 
*   **Server Locations / Sovereignty:**
    *   For EU users, hosting databases and processing nodes in an EU region (e.g., Frankfurt) is essential to simplify GDPR compliance and avoid cross-border data transfer headaches.

## 2. Age-Gating and Content Liability

Even for purely synthetic AI entities, age restrictions and content liability laws strictly apply.

*   **COPPA (Children's Online Privacy Protection Act - US):**
    *   Strictly prohibits collecting data from children under 13 without parental consent.
    *   *Action:* Amorien MUST enforce a strict 18+ policy. Ensure marketing and UI do not inadvertently target children.
*   **FOSTA-SESTA (US):**
    *   Designed to combat sex trafficking. While Amorien is a simulated AI (not connecting humans), the platform must aggressively police any user attempts to generate CSAM or use the AI to organize illegal human activities. 
    *   *Payment Processors (Stripe, PayPal):* Are highly sensitive to FOSTA-SESTA and "adult" themes. If Amorien ventures into NSFW territory, mainstream processors may ban the account. *Action:* Consider high-risk merchant processors (e.g., CCBill) or implement strict content filters to stay within Stripe's AUP.
*   **Age Verification Mechanisms:**
    *   If the AI is purely SFW, a standard self-declaration (checkbox) during signup is typical.
    *   If NSFW features are unlocked, consider robust age-verification (e.g., ID check via a provider like Yoti or Stripe Identity) to shield against liability.

## 3. Privacy & Biometric Compliance (Video/Audio)

Processing voice and video introduces extreme regulatory scrutiny because it involves biometric identifiers.

*   **GDPR (EU) & UK GDPR:**
    *   *Basis of Processing:* Requires explicit consent.
    *   *Right to be Forgotten:* Users must have a 1-click option to delete all their chats, voice history, and video data. 
    *   *Action:* Ensure database architecture supports hard-deleting a user's unified data profile seamlessly.
*   **CCPA / CPRA (California):**
    *   Requires clear disclosure of data collection and a "Do Not Sell My Personal Information" mechanism.
*   **Biometric Laws (e.g., BIPA - Illinois):**
    *   If Amorien analyzes user webcam feeds for emotion tracking, or records user voice to adapt its responses, this falls under strict biometric privacy acts.
    *   *Action:* Strictly avoid storing specific voiceprints or facial geometry unless absolutely core to the product. If required, obtain distinct, written, opt-in consent detailing retention and destruction timelines.

## 4. Data Retention & Security Policy

Trust is the product when hosting private companions. Data architectures should adopt a "Zero-Trust" or "Privacy-by-Design" approach.

*   **Chat Logs & Memories:**
    *   Data should be encrypted at rest (AES-256) and in transit (TLS 1.3).
    *   Consider implementing RAG (Retrieval-Augmented Generation) architectures where episodic memories are encrypted with a key derived from the user's password, ensuring internal staff cannot read private 1-on-1 chats.
*   **Audio/Video Retention:**
    *   *Input Data:* Delete incoming user audio immediately after transcription (Speech-to-Text). Do not store the waveform unless explicitly requested by the user.
    *   *Generated Data:* AI-generated video and audio should be streamed to the user and cached only temporarily. 
*   **Incident Response:** Plan for mandatory breach notifications (within 72 hours under GDPR) if the companion database is compromised.

## 5. Immediate Action Plan

1.  **Draft Policies:** Engage legal counsel to draft a robust Terms of Service (ToS) and Privacy Policy tailored to *synthetic relationships* and *biometric processing*.
2.  **Separate Infrastructure:** Route open-source/uncensored AI workloads to specialized GPU clouds (e.g., RunPod) and safe backend logic to AWS/GCP.
3.  **Payment Gateway Alignment:** Review Stripe's restricted business list vs. your prompt limitations. Choose CCBill/Epoch if pursuing fully uncensored paths.
4.  **Implement 'Kill Switch':** Build account-deletion tools before launch to comply with GDPR/CCPA data destruction mandates. 
