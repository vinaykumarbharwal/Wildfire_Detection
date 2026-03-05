# 🤖 Making n8n Alerts Permanent

To stop having to copy the token every hour, you can link your `firebase-credentials.json` directly into n8n. 

Follow these 3 simple steps:

### 1. Add Credentials to n8n
1.  Open your n8n dashboard (usually `http://localhost:5678`).
2.  On the left sidebar, click **Credentials**.
3.  Click **Add Credential** (top right).
4.  Search for **"Google Firebase Cloud Messaging"**.
5.  Open your `backend/firebase-credentials.json` file in a text editor.
6.  **Copy everything** inside that file and paste it into the **"Service Account Key"** box in n8n.
7.  Click **Save**.

### 2. Update the Workflow Node
1.  Go to your workflow in n8n.
2.  Open the **"Send Push Notification"** node.
3.  In the **Credential** dropdown, select the one you just created ("Firebase Service Account").
4.  Note: I have already updated the [fire-alert.json](file:///c:/Users/Vinay%20kumar/Project_Fire/automation/n8n_workflows/fire-alert.json) file to use this modern node for you.

### 3. Clean up your .env
Once this is working, you **no longer need** `GOOGLE_ACCESS_TOKEN` in your `.env` file! n8n will handle the token refresh automatically forever.

---

> [!TIP]
> This is exactly how professional systems handle notifications. Once set, you can forget about it!
