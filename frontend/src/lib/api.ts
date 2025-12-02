import { format } from "date-fns";

export type PolicyType = 
  | "confidentiality"
  | "external_communication"
  | "data_privacy"
  | "security"
  | "hr";

export interface PolicyDocument {
  id: number;
  title: string;
  file_path: string;
  policy_type: PolicyType;
  department?: string;
  version?: string;
  created_at: string;
}

export interface ComplianceIssue {
  type: string;
  policy_reference?: string;
  excerpt?: string;
  explanation: string;
}

export interface ComplianceCheckResponse {
  overall_risk: "NONE" | "LOW" | "MEDIUM" | "HIGH";
  issues: ComplianceIssue[];
  suggested_text?: string | null;
}

export interface ComplianceCheckLog {
  id: number;
  created_at: string;
  text: string;
  department?: string;
  policy_type?: PolicyType;
  overall_risk: "NONE" | "LOW" | "MEDIUM" | "HIGH";
  issues?: ComplianceIssue[];
  suggested_text?: string | null;
}

// Mock Data Store
let policies: PolicyDocument[] = [
  {
    id: 1,
    title: "Data Privacy Policy 2024",
    file_path: "/storage/policies/privacy_2024.pdf",
    policy_type: "data_privacy",
    department: "Legal",
    version: "1.2",
    created_at: new Date(Date.now() - 10000000).toISOString(),
  },
  {
    id: 2,
    title: "Social Media Guidelines",
    file_path: "/storage/policies/social_media.pdf",
    policy_type: "external_communication",
    department: "Marketing",
    version: "2.0",
    created_at: new Date(Date.now() - 5000000).toISOString(),
  },
  {
    id: 3,
    title: "IT Security Standards",
    file_path: "/storage/policies/security.pdf",
    policy_type: "security",
    department: "IT",
    version: "1.0",
    created_at: new Date(Date.now() - 20000000).toISOString(),
  }
];

let logs: ComplianceCheckLog[] = [
  {
    id: 101,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    text: "We are excited to announce our new partnership with Acme Corp! The deal is worth $5M.",
    department: "Sales",
    policy_type: "external_communication",
    overall_risk: "HIGH",
    issues: [
      {
        type: "Confidentiality",
        policy_reference: "Ext. Comm Policy §4.1",
        excerpt: "The deal is worth $5M",
        explanation: "Financial details of partnerships are confidential until official press release."
      }
    ],
    suggested_text: "We are excited to announce our new partnership with Acme Corp! This strategic alliance will bring great value."
  },
  {
    id: 102,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    text: "Hey team, remember to change your passwords by Friday.",
    department: "IT",
    policy_type: "security",
    overall_risk: "NONE",
    issues: [],
    suggested_text: null
  },
  {
    id: 103,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    text: "Customer John Doe (SSN: 123-45-6789) requested a refund.",
    department: "Support",
    policy_type: "data_privacy",
    overall_risk: "HIGH",
    issues: [
      {
        type: "PII Violation",
        policy_reference: "Data Privacy Act §2",
        excerpt: "SSN: 123-45-6789",
        explanation: "Never share full SSNs in support tickets or internal chats."
      }
    ],
    suggested_text: "Customer John Doe (ID: ****6789) requested a refund."
  }
];

// Mock API Functions
export const api = {
  checkCompliance: async (text: string, department?: string, policy_type?: string): Promise<ComplianceCheckResponse> => {
    await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate network delay

    // Simple keyword-based mock logic for demo purposes
    const lowerText = text.toLowerCase();
    let risk: "NONE" | "LOW" | "MEDIUM" | "HIGH" = "NONE";
    const issues: ComplianceIssue[] = [];
    let suggested_text = null;

    if (lowerText.includes("ssn") || lowerText.includes("password") || lowerText.includes("secret")) {
      risk = "HIGH";
      issues.push({
        type: "Security Violation",
        policy_reference: "Security Policy §1.2",
        excerpt: "secret/password/ssn",
        explanation: "Sensitive information detected. Do not share credentials or PII."
      });
      suggested_text = text.replace(/ssn|password|secret/gi, "[REDACTED]");
    } else if (lowerText.includes("promise") || lowerText.includes("guarantee")) {
      risk = "MEDIUM";
      issues.push({
        type: "Liability Risk",
        policy_reference: "External Comm §3.5",
        excerpt: "guarantee/promise",
        explanation: "Avoid making absolute guarantees that create legal liability."
      });
      suggested_text = text.replace(/guarantee|promise/gi, "strive to ensure");
    } else if (lowerText.includes("urgent") || lowerText.includes("asap")) {
      risk = "LOW";
      issues.push({
        type: "Tone Check",
        policy_reference: "HR Communication Guidelines",
        excerpt: "urgent/asap",
        explanation: "Consider a more collaborative tone."
      });
      suggested_text = text.replace(/urgent|asap/gi, "when possible");
    }

    // Log the check
    const newLog: ComplianceCheckLog = {
      id: Math.floor(Math.random() * 10000),
      created_at: new Date().toISOString(),
      text,
      department,
      policy_type: policy_type as PolicyType,
      overall_risk: risk,
      issues,
      suggested_text
    };
    logs.unshift(newLog);

    return {
      overall_risk: risk,
      issues,
      suggested_text
    };
  },

  getLogs: async (department?: string, risk?: string): Promise<ComplianceCheckLog[]> => {
    await new Promise(resolve => setTimeout(resolve, 600));
    let filtered = [...logs];
    if (department) filtered = filtered.filter(l => l.department === department);
    if (risk) filtered = filtered.filter(l => l.overall_risk === risk);
    return filtered;
  },

  getPolicies: async (): Promise<PolicyDocument[]> => {
    await new Promise(resolve => setTimeout(resolve, 600));
    return [...policies];
  },

  uploadPolicy: async (file: File, title: string, type: string, department?: string): Promise<PolicyDocument> => {
    await new Promise(resolve => setTimeout(resolve, 2000));
    const newDoc: PolicyDocument = {
      id: Math.floor(Math.random() * 1000),
      title,
      file_path: `/storage/policies/${file.name}`,
      policy_type: type as PolicyType,
      department,
      version: "1.0",
      created_at: new Date().toISOString()
    };
    policies.unshift(newDoc);
    return newDoc;
  }
};
