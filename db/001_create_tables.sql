-- ====================================================================
-- AI Proposal Assistant - Database Schema (Sprint 0)
-- File: 001_create_tables.sql
-- Owner: Likhitha Yada (Track A)
-- Reviewer: Charishma M (Track A Lead)
-- Note: Every table enforces opportunityId for multi-bid isolation.
-- ====================================================================

-- 1. Table: Opportunity (The central bid record)
CREATE TABLE Opportunity (
    opportunityId VARCHAR(50) PRIMARY KEY,
    clientName VARCHAR(100) NOT NULL,
    bidTitle VARCHAR(255) NOT NULL,
    circle VARCHAR(50) NOT NULL,          -- Enterprise, Healthcare, Financial Services, etc.
    currentStage VARCHAR(50) NOT NULL,    -- New, In analysis, Drafting, Awaiting SME, In approval, Submitted
    status VARCHAR(50) NOT NULL,          -- Active, Won, Lost, Paused
    bidOwnerEmail VARCHAR(100) NOT NULL,
    dueDate DATETIME2 NOT NULL,
    createdAt DATETIME2 DEFAULT SYSUTCDATETIME()
);

-- 2. Table: StageHistory (Required by Charishma's orchestrator on Monday!)
CREATE TABLE StageHistory (
    historyId INT IDENTITY(1,1) PRIMARY KEY,
    opportunityId VARCHAR(50) NOT NULL,
    stage VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,          -- Started, Completed, Paused, Rejected
    updatedBy VARCHAR(100) NOT NULL,
    notes NVARCHAR(MAX) NULL,
    timestamp DATETIME2 DEFAULT SYSUTCDATETIME(),
    FOREIGN KEY (opportunityId) REFERENCES Opportunity(opportunityId)
);

-- 3. Table: Document (Stores uploaded RFPs, past wins, and generated packs)
CREATE TABLE Document (
    documentId VARCHAR(50) PRIMARY KEY,
    opportunityId VARCHAR(50) NOT NULL,
    fileName VARCHAR(255) NOT NULL,
    fileType VARCHAR(20) NOT NULL,        -- PDF, DOCX, XLSX
    storageUrl NVARCHAR(500) NOT NULL,
    docType VARCHAR(50) NOT NULL,         -- RFP, PastWin, DraftPack, SubmissionPack
    version INT DEFAULT 1,
    uploadedAt DATETIME2 DEFAULT SYSUTCDATETIME(),
    FOREIGN KEY (opportunityId) REFERENCES Opportunity(opportunityId)
);

-- 4. Table: Requirement (Extracted requirements from the Intake Agent)
CREATE TABLE Requirement (
    requirementId VARCHAR(50) PRIMARY KEY,
    opportunityId VARCHAR(50) NOT NULL,
    reqCode VARCHAR(50) NOT NULL,         -- e.g. REQ-SEC-001
    requirementText NVARCHAR(MAX) NOT NULL,
    sectionRef VARCHAR(100) NULL,         -- e.g. Section 4.2
    category VARCHAR(50) NOT NULL,        -- Technical, Pricing, Legal, Functional
    isMandatory BIT DEFAULT 1,
    FOREIGN KEY (opportunityId) REFERENCES Opportunity(opportunityId)
);

-- 5. Table: DraftSection (Generated proposal sections from Drafting Agent)
CREATE TABLE DraftSection (
    sectionId VARCHAR(50) PRIMARY KEY,
    opportunityId VARCHAR(50) NOT NULL,
    sectionName VARCHAR(100) NOT NULL,    -- Executive Summary, Scope, Assumptions, etc.
    content NVARCHAR(MAX) NOT NULL,
    citations NVARCHAR(MAX) NULL,         -- JSON array of source citations
    version INT DEFAULT 1,
    needsSmeReview BIT DEFAULT 0,
    updatedAt DATETIME2 DEFAULT SYSUTCDATETIME(),
    FOREIGN KEY (opportunityId) REFERENCES Opportunity(opportunityId)
);

-- 6. Table: Gap (Unanswered requirements routed to SMEs in Teams)
CREATE TABLE Gap (
    gapId VARCHAR(50) PRIMARY KEY,
    opportunityId VARCHAR(50) NOT NULL,
    requirementId VARCHAR(50) NOT NULL,
    gapType VARCHAR(50) NOT NULL,         -- Technical, Pricing, Legal
    clarificationQuestion NVARCHAR(MAX) NOT NULL,
    assignedSmeEmail VARCHAR(100) NULL,
    smeReply NVARCHAR(MAX) NULL,
    status VARCHAR(50) DEFAULT 'Open',    -- Open, Awaiting SME, Resolved, Waived
    FOREIGN KEY (opportunityId) REFERENCES Opportunity(opportunityId),
    FOREIGN KEY (requirementId) REFERENCES Requirement(requirementId)
);

-- 7. Table: ActionItem (Action items and deadline nudges in Teams)
CREATE TABLE ActionItem (
    actionId VARCHAR(50) PRIMARY KEY,
    opportunityId VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    assignedToEmail VARCHAR(100) NOT NULL,
    dueDate DATETIME2 NOT NULL,
    isCompleted BIT DEFAULT 0,
    FOREIGN KEY (opportunityId) REFERENCES Opportunity(opportunityId)
);

-- 8. Table: AuditLog (Tracks every prompt run, card click, and approver action)
CREATE TABLE AuditLog (
    auditId INT IDENTITY(1,1) PRIMARY KEY,
    opportunityId VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,         -- e.g. PromptRun, GapAssigned, ApproverSigned
    actorEmail VARCHAR(100) NOT NULL,
    details NVARCHAR(MAX) NULL,
    timestamp DATETIME2 DEFAULT SYSUTCDATETIME(),
    FOREIGN KEY (opportunityId) REFERENCES Opportunity(opportunityId)
);
