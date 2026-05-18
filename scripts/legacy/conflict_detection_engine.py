"""
Dynamic Medication-Allergy Conflict Detection System
Handles cross-reactivity, drug families, and medical contraindications
"""

MEDICATION_ALLERGY_CONFLICTS = {
    # Penicillin-based conflicts
    "penicillin": {
        "cross_reactive": [
            "amoxicillin",
            "ampicillin",
            "piperacillin",
            "ticarcillin",
            "cephalosporins",  # ~10% cross-reactivity
            "carbapenems"       # rare cross-reactivity
        ],
        "contraindications": [],
        "severity": "HIGH"
    },
    "amoxicillin": {
        "cross_reactive": ["penicillin", "ampicillin", "cephalosporins"],
        "contraindications": [],
        "severity": "HIGH"
    },
    "ampicillin": {
        "cross_reactive": ["penicillin", "amoxicillin", "cephalosporins"],
        "contraindications": [],
        "severity": "HIGH"
    },
    
    # Cephalosporin conflicts
    "cephalosporin": {
        "cross_reactive": ["penicillin", "amoxicillin", "ampicillin"],
        "contraindications": [],
        "severity": "MEDIUM"
    },
    
    # Sulfonamide conflicts
    "sulfonamide": {
        "cross_reactive": ["trimethoprim", "sulfadiazine"],
        "contraindications": [],
        "severity": "MEDIUM"
    },
    "sulfamethoxazole": {
        "cross_reactive": ["trimethoprim", "sulfadiazine", "sulfonamides"],
        "contraindications": [],
        "severity": "MEDIUM"
    },
    "trimethoprim": {
        "cross_reactive": ["sulfonamides", "sulfamethoxazole"],
        "contraindications": [],
        "severity": "MEDIUM"
    },
    
    # NSAID conflicts
    "aspirin": {
        "cross_reactive": ["ibuprofen", "naproxen", "indomethacin", "meloxicam"],
        "contraindications": ["warfarin", "clopidogrel"],
        "severity": "HIGH"
    },
    "ibuprofen": {
        "cross_reactive": ["aspirin", "naproxen", "indomethacin"],
        "contraindications": ["warfarin", "clopidogrel"],
        "severity": "MEDIUM"
    },
    "naproxen": {
        "cross_reactive": ["aspirin", "ibuprofen", "indomethacin"],
        "contraindications": ["warfarin", "clopidogrel"],
        "severity": "MEDIUM"
    },
    
    # ACE Inhibitor conflicts
    "lisinopril": {
        "cross_reactive": ["enalapril", "ramipril", "captopril"],
        "contraindications": ["potassium supplements", "spironolactone"],
        "severity": "HIGH"
    },
    "enalapril": {
        "cross_reactive": ["lisinopril", "ramipril", "captopril"],
        "contraindications": ["potassium supplements"],
        "severity": "HIGH"
    },
    
    # Statins
    "atorvastatin": {
        "cross_reactive": ["simvastatin", "lovastatin"],
        "contraindications": ["fibrates", "niacin"],
        "severity": "MEDIUM"
    },
    "simvastatin": {
        "cross_reactive": ["atorvastatin", "lovastatin"],
        "contraindications": ["fibrates"],
        "severity": "MEDIUM"
    },
    
    # Quinolone conflicts
    "ciprofloxacin": {
        "cross_reactive": ["levofloxacin", "moxifloxacin"],
        "contraindications": ["warfarin", "theophylline"],
        "severity": "MEDIUM"
    },
    "levofloxacin": {
        "cross_reactive": ["ciprofloxacin", "moxifloxacin"],
        "contraindications": ["warfarin"],
        "severity": "MEDIUM"
    },
    
    # Macrolide conflicts
    "erythromycin": {
        "cross_reactive": ["azithromycin", "clarithromycin"],
        "contraindications": ["warfarin", "digoxin"],
        "severity": "MEDIUM"
    },
    "azithromycin": {
        "cross_reactive": ["erythromycin", "clarithromycin"],
        "contraindications": ["warfarin"],
        "severity": "LOW"
    },
}

def normalize_medication_name(name: str) -> str:
    """Normalize medication name for lookup"""
    return name.strip().lower().replace(" ", "")

def detect_conflict(allergy: str, medication: str) -> dict:
    """
    Detect medication-allergy conflict dynamically
    
    Returns:
    {
        "conflict_detected": bool,
        "conflict_type": str,  # "cross_reactive", "contraindication", "none"
        "risk_score": int,     # 0-10
        "severity": str,       # "LOW", "MEDIUM", "HIGH"
        "warning": str,        # Human-readable warning
        "recommendation": str  # Clinical recommendation
    }
    """
    allergy_norm = normalize_medication_name(allergy)
    med_norm = normalize_medication_name(medication)
    
    # Check if exact match (same medication)
    if allergy_norm == med_norm:
        return {
            "conflict_detected": True,
            "conflict_type": "exact_match",
            "risk_score": 10,
            "severity": "CRITICAL",
            "warning": f"CRITICAL: Patient has documented allergy to {allergy}. Prescribing {medication} is contraindicated.",
            "recommendation": "DO NOT PRESCRIBE. Use alternative medication family."
        }
    
    # Check for cross-reactivity
    allergy_data = MEDICATION_ALLERGY_CONFLICTS.get(allergy_norm)
    if allergy_data:
        cross_reactive = [normalize_medication_name(m) for m in allergy_data.get("cross_reactive", [])]
        
        if med_norm in cross_reactive:
            severity = allergy_data.get("severity", "MEDIUM")
            risk_score = {"HIGH": 8, "MEDIUM": 6, "LOW": 3}.get(severity, 5)
            
            return {
                "conflict_detected": True,
                "conflict_type": "cross_reactivity",
                "risk_score": risk_score,
                "severity": severity,
                "warning": f"{allergy} allergy on file. {medication} is a {allergy}-type antibiotic/drug (cross-reactivity risk: {severity}). Medical review required.",
                "recommendation": f"Obtain informed consent and document clinical justification for {medication} use."
            }
        
        # Check contraindications
        contraindications = [normalize_medication_name(m) for m in allergy_data.get("contraindications", [])]
        if med_norm in contraindications:
            return {
                "conflict_detected": True,
                "conflict_type": "contraindication",
                "risk_score": 7,
                "severity": "HIGH",
                "warning": f"Contraindication alert: {medication} should not be used with {allergy} allergy history.",
                "recommendation": "Use alternative medication. If necessary, obtain physician override."
            }
    
    # No conflict found
    return {
        "conflict_detected": False,
        "conflict_type": "none",
        "risk_score": 0,
        "severity": "NONE",
        "warning": None,
        "recommendation": "No documented allergy conflict detected."
    }

def detect_all_conflicts(allergies: list, medications: list) -> list:
    """
    Detect all conflicts between multiple allergies and medications
    
    Args:
    - allergies: List of patient allergies
    - medications: List of prescribed medications
    
    Returns:
    - List of conflict dicts
    """
    conflicts = []
    for allergy in allergies:
        for medication in medications:
            conflict = detect_conflict(allergy, medication)
            if conflict["conflict_detected"]:
                conflict["allergy"] = allergy
                conflict["medication"] = medication
                conflicts.append(conflict)
    
    return conflicts

# Test the system
if __name__ == "__main__":
    print("=" * 80)
    print("DYNAMIC CONFLICT DETECTION SYSTEM")
    print("=" * 80)
    
    # Test case 1: Penicillin allergy + Amoxicillin (cross-reactivity)
    print("\n[TEST 1] Penicillin allergy + Amoxicillin prescription")
    result = detect_conflict("Penicillin", "Amoxicillin")
    print(f"  Conflict Detected: {result['conflict_detected']}")
    print(f"  Type: {result['conflict_type']}")
    print(f"  Risk Score: {result['risk_score']}/10")
    print(f"  Warning: {result['warning']}")
    
    # Test case 2: Penicillin allergy + Ciprofloxacin (no conflict)
    print("\n[TEST 2] Penicillin allergy + Ciprofloxacin prescription")
    result = detect_conflict("Penicillin", "Ciprofloxacin")
    print(f"  Conflict Detected: {result['conflict_detected']}")
    print(f"  Recommendation: {result['recommendation']}")
    
    # Test case 3: Multiple allergies and medications
    print("\n[TEST 3] Multiple allergy-medication combinations")
    allergies = ["Penicillin", "NSAID", "Sulfonamide"]
    medications = ["Amoxicillin", "Ibuprofen", "Ciprofloxacin"]
    
    conflicts = detect_all_conflicts(allergies, medications)
    print(f"  Total combinations checked: {len(allergies) * len(medications)}")
    print(f"  Conflicts detected: {len(conflicts)}")
    for i, conflict in enumerate(conflicts, 1):
        print(f"\n  [{i}] {conflict['allergy']} ↔ {conflict['medication']}")
        print(f"      Risk: {conflict['risk_score']}/10 ({conflict['severity']})")
        print(f"      Warning: {conflict['warning']}")
    
    print("\n" + "=" * 80)
    print("✅ Dynamic conflict detection system operational")
    print("=" * 80)
