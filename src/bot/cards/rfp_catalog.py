"""RFP catalog and Adaptive Card generators for repository sample documents."""
from typing import Dict, Any, Optional
from microsoft_teams.cards import AdaptiveCard

# Repository sample RFPs located in samples/rfp/
SAMPLE_RFPS: Dict[str, Dict[str, Any]] = {
    "harborline": {
        "id": "1",
        "key": "harborline",
        "client": "Harborline Mutual Insurance Company",
        "rfp_id": "HMI-IT-2026-114",
        "file_source": "samples/rfp/SAMPLE_RFP_01_Harborline_Claims_Modernisation.docx",
        "scope": "Claims Platform Modernisation & AI-Assisted Claims Triage",
        "due_date": "December 4, 2026 (17:00 US Eastern)",
        "circle": "Financial Services & Insurance Circle",
        "icon": "🛡",
        "team": {
            "Lead Solution Architect:": "Sarah Jenkins (Cloud Migration & Claims Modernisation CoE)",
            "Bid Manager:": "Michael Chang (Presales Operations)",
            "Domain SME:": "David Kumar (P&C Insurance & Claims Triage)"
        }
    },
    "cedarbrook": {
        "id": "2",
        "key": "cedarbrook",
        "client": "Cedarbrook Health System",
        "rfp_id": "CHS-RFI-2026-042",
        "file_source": "samples/rfp/SAMPLE_RFI_02_Cedarbrook_Data_Platform.pdf",
        "scope": "Enterprise Data Platform & Clinical Analytics Modernisation",
        "due_date": "December 11, 2026 (17:00 US Eastern)",
        "circle": "Healthcare & Life Sciences Circle",
        "icon": "🏥",
        "team": {
            "Lead Solution Architect:": "Elena Rostova (Healthcare Data & FHIR CoE)",
            "Bid Manager:": "Jordan Lee (Presales Operations)",
            "Domain SME:": "Dr. Marcus Vance (Clinical Informatics)"
        }
    },
    "velora": {
        "id": "3",
        "key": "velora",
        "client": "Velora Retail Group plc",
        "rfp_id": "VRG-ITT-2026-088",
        "file_source": "samples/rfp/SAMPLE_RFP_03_Velora_Search_Managed_Services.pdf",
        "scope": "E-commerce Search, Personalisation & Managed Services",
        "due_date": "December 15, 2026 (17:00 GMT)",
        "circle": "Retail & Consumer Goods Circle",
        "icon": "🛍",
        "team": {
            "Lead Solution Architect:": "Priya Sharma (Retail Commerce & Search CoE)",
            "Bid Manager:": "Michael Chang (Presales Operations)",
            "Domain SME:": "Oliver Bennett (Customer Experience & AI Recommenders)"
        }
    }
}


def get_rfp_by_query(query: str) -> Optional[Dict[str, Any]]:
    """Resolve an RFP entry from a number ('1', '2', '3') or keyword ('cedarbrook', 'velora')."""
    q = query.strip().lower()
    for key, rfp in SAMPLE_RFPS.items():
        if q == key or q == rfp["id"] or q in rfp["client"].lower() or q in rfp["circle"].lower():
            return rfp
    return None


def create_intake_card(rfp: Dict[str, Any]) -> AdaptiveCard:
    """Generate Step 2 RFP Intake Adaptive Card for a specific repository document."""
    card_dict = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": rfp.get("icon", "📋"),
                                        "size": "ExtraLarge"
                                    }
                                ]
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"New RFP Intake: {rfp['scope']}",
                                        "weight": "Bolder",
                                        "size": "Large",
                                        "wrap": True
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": f"Source: {rfp['file_source']}",
                                        "size": "Small",
                                        "isSubtle": True,
                                        "spacing": "None",
                                        "wrap": True
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "type": "Container",
                "spacing": "Medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "Opportunity Overview",
                        "weight": "Bolder",
                        "size": "Medium",
                        "wrap": True
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": "Client:", "value": rfp["client"]},
                            {"title": "RFP Reference:", "value": rfp["rfp_id"]},
                            {"title": "RFP Due Date:", "value": rfp["due_date"]},
                            {"title": "Target Circle:", "value": rfp["circle"]},
                            {"title": "Scope:", "value": rfp["scope"]},
                            {"title": "Status:", "value": "Pending Pre-Sales Confirmation (business_flow_v2, Step 2)"}
                        ]
                    }
                ]
            },
            {
                "type": "Container",
                "style": "default",
                "spacing": "Medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "👥 Suggested Bid Team (AI Match)",
                        "weight": "Bolder",
                        "size": "Medium",
                        "wrap": True
                    },
                    {
                        "type": "FactSet",
                        "facts": [{"title": role, "value": member} for role, member in rfp["team"].items()]
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Assign bid owner",
                "data": {
                    "action": "assign_bid_owner",
                    "rfpId": rfp["rfp_id"],
                    "client": rfp["client"],
                    "circle": rfp["circle"]
                }
            },
            {
                "type": "Action.Submit",
                "title": "Confirm team",
                "style": "positive",
                "data": {
                    "action": "confirm_team",
                    "rfpId": rfp["rfp_id"],
                    "client": rfp["client"],
                    "circle": rfp["circle"]
                }
            }
        ]
    }
    return AdaptiveCard.model_validate(card_dict)


def create_rfp_selector_card() -> AdaptiveCard:
    """Generate an interactive selector card listing all 3 repository sample RFPs."""
    card_dict = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "📂 Repository RFP Intake Hub",
                        "weight": "Bolder",
                        "size": "Large",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": "Select a client document from 'samples/rfp/' to view its Step 2 Intake Card:",
                        "isSubtle": True,
                        "wrap": True,
                        "spacing": "Small"
                    }
                ]
            },
            {
                "type": "Container",
                "spacing": "Medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "1. 🛡 Harborline Mutual Insurance Company",
                        "weight": "Bolder",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": "• Circle: Financial Services & Insurance\n• Scope: Claims Platform Modernisation & AI Triage\n• File: `SAMPLE_RFP_01_Harborline_Claims_Modernisation.docx`",
                        "size": "Small",
                        "isSubtle": True,
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": "2. 🏥 Cedarbrook Health System",
                        "weight": "Bolder",
                        "wrap": True,
                        "spacing": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": "• Circle: Healthcare & Life Sciences\n• Scope: Enterprise Data Platform & Clinical Analytics\n• File: `SAMPLE_RFI_02_Cedarbrook_Data_Platform.pdf`",
                        "size": "Small",
                        "isSubtle": True,
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": "3. 🛍 Velora Retail Group plc",
                        "weight": "Bolder",
                        "wrap": True,
                        "spacing": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": "• Circle: Retail & Consumer Goods\n• Scope: E-Commerce Search, Personalisation & Services\n• File: `SAMPLE_RFP_03_Velora_Search_Managed_Services.pdf`",
                        "size": "Small",
                        "isSubtle": True,
                        "wrap": True
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "1. 🛡 Harborline",
                "data": {"action": "select_rfp", "target": "harborline"}
            },
            {
                "type": "Action.Submit",
                "title": "2. 🏥 Cedarbrook",
                "data": {"action": "select_rfp", "target": "cedarbrook"}
            },
            {
                "type": "Action.Submit",
                "title": "3. 🛍 Velora",
                "data": {"action": "select_rfp", "target": "velora"}
            }
        ]
    }
    return AdaptiveCard.model_validate(card_dict)
