-- ====================================================================
-- AI Proposal Assistant - Seed Data (Sprint 0)
-- File: 002_seed_data.sql
-- Owner: Likhitha Yada (Track A)
-- Purpose: Seed data for 2 sample opportunities for early testing.
-- ====================================================================

-- 1. Insert 2 Sample Opportunities
INSERT INTO Opportunity (opportunityId, clientName, bidTitle, circle, currentStage, status, bidOwnerEmail, dueDate)
VALUES 
('OPP-2026-001', 'Contoso Healthcare', 'Cloud Modernization RFP', 'Healthcare', 'In analysis', 'Active', 'likhitha.yada@ascendion.com', '2026-12-15 17:00:00'),
('OPP-2026-002', 'Fabrikam Financial', 'Generative AI Analytics Platform', 'Enterprise', 'Drafting', 'Active', 'charishma.m@ascendion.com', '2026-12-20 17:00:00');

-- 2. Insert Stage History records (Simulating progression)
INSERT INTO StageHistory (opportunityId, stage, status, updatedBy, notes)
VALUES 
('OPP-2026-001', 'New', 'Completed', 'system', 'RFP detected from SharePoint drop'),
('OPP-2026-001', 'In analysis', 'Started', 'charishma.m@ascendion.com', 'Intake agent parsing started'),
('OPP-2026-002', 'New', 'Completed', 'system', 'Bid created via Teams + New Proposal'),
('OPP-2026-002', 'Drafting', 'Started', 'charishma.m@ascendion.com', 'Straw-man drafting in progress');

-- 3. Insert Sample Extracted Requirements for OPP-2026-001
INSERT INTO Requirement (requirementId, opportunityId, reqCode, requirementText, sectionRef, category, isMandatory)
VALUES
('REQ-001', 'OPP-2026-001', 'REQ-SEC-01', 'The cloud platform must comply with HIPAA and ISO 27001 security standards.', 'Section 4.1', 'Security', 1),
('REQ-002', 'OPP-2026-001', 'REQ-ARC-02', 'Solution must support hybrid cloud migration using Azure Arc or native Azure VPN.', 'Section 5.3', 'Technical', 1),
('REQ-003', 'OPP-2026-001', 'REQ-PRI-03', 'Vendor must provide rate cards for L1 through L3 cloud support engineers.', 'Section 8.2', 'Pricing', 0);

-- 4. Insert Sample Draft Section for OPP-2026-002
INSERT INTO DraftSection (sectionId, opportunityId, sectionName, content, citations, version, needsSmeReview)
VALUES
('SEC-001', 'OPP-2026-002', 'Executive Summary', 'Ascendion proposes an enterprise AI analytics platform built on Azure OpenAI and Databricks...', '["PastWin-Fabrikam-2025-Sec2", "RFP-Section-1.2"]', 1, 0);

-- 5. Insert Sample Gap for OPP-2026-001
INSERT INTO Gap (gapId, opportunityId, requirementId, gapType, clarificationQuestion, assignedSmeEmail, status)
VALUES
('GAP-001', 'OPP-2026-001', 'REQ-001', 'Security', 'Can Ascendion provide the latest BAA and SOC 2 Type II report for our healthcare cloud landing zone?', 'sme-security@ascendion.com', 'Open');
