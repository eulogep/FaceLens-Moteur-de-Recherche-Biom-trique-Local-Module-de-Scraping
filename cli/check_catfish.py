import os
import sys
import argparse
import csv
import numpy as np
from typing import List, Tuple, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import settings
from core.face_engine import get_face_engine

def parse_args():
    parser = argparse.ArgumentParser(
        description="FaceLens Catfish Checker CLI - Comparaison d'une photo suspecte avec un dossier ou CSV de candidats."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Chemin vers la photo du visage suspect à vérifier."
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help="Dossier d'images candidates OU fichier CSV (format 'chemin|nom')."
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Nombre de résultats maximum à récapituler (défaut: 10)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation : évalue les ressemblance sans écrire ni modifier d'index ou de base de données."
    )
    return parser.parse_args()

def load_candidates(candidates_path: str) -> List[Tuple[str, str]]:
    """
    Loads candidates as list of tuples (file_path, person_name).
    """
    candidates = []
    if os.path.isfile(candidates_path) and candidates_path.endswith(".csv"):
        with open(candidates_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="|")
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                path = row[0].strip()
                name = row[1].strip() if len(row) > 1 else os.path.basename(path)
                if os.path.exists(path):
                    candidates.append((path, name))
    elif os.path.isdir(candidates_path):
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        for root, _, files in os.walk(candidates_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    full_path = os.path.join(root, file)
                    base_name = os.path.splitext(file)[0].replace("_", " ").replace("-", " ")
                    candidates.append((full_path, base_name))
    else:
        raise ValueError(f"Chemin de candidats invalide (ni dossier ni fichier CSV existant): {candidates_path}")

    return candidates

def main():
    args = parse_args()
    engine = get_face_engine()

    print("=" * 80)
    print("  FACELENS - CORRESPONDANCE BIOMÉTRIQUE & CATFISH CHECKER")
    if args.dry_run:
        print("  [MODE DRY-RUN ACTIVÉ : Aucune donnée ne sera sauvegardée]")
    print("=" * 80)
    print(f"Photo cible suspecte : {args.target}")

    if not os.path.exists(args.target):
        print(f"Erreur : Fichier cible introuvable : {args.target}")
        sys.exit(1)

    target_faces = engine.extract_faces(args.target)
    if not target_faces:
        print("Avertissement : Aucun visage n'a été détecté dans l'image cible.")
        print(f"\nAvertissement Légal :\n{settings.DISCLAIMER}\n")
        sys.exit(0)

    target_vector = max(target_faces, key=lambda f: f["det_score"])["embedding"]

    try:
        candidates = load_candidates(args.candidates)
    except Exception as e:
        print(f"Erreur lors du chargement des candidats : {e}")
        sys.exit(1)

    print(f"Candidats trouvés : {len(candidates)} photo(s)")
    print("-" * 80)

    results = []
    for cand_path, cand_name in candidates:
        try:
            cand_faces = engine.extract_faces(cand_path)
            if not cand_faces:
                continue

            cand_vector = max(cand_faces, key=lambda f: f["det_score"])["embedding"]
            similarity = float(np.dot(target_vector, cand_vector))
            distance = float(1.0 - similarity)

            if similarity >= settings.THRESHOLD_STRONG:
                verdict = "FORT"
            elif similarity >= settings.THRESHOLD_MEDIUM:
                verdict = "MOYEN"
            else:
                verdict = "SOSIE" if similarity >= settings.THRESHOLD_LOOKALIKE else "FAUX POSITIF"

            results.append({
                "file": os.path.basename(cand_path),
                "name": cand_name,
                "similarity": similarity,
                "distance": distance,
                "verdict": verdict,
                "path": cand_path
            })
        except Exception as e:
            continue

    # Sort descending by similarity
    results.sort(key=lambda r: r["similarity"], reverse=True)
    top_results = results[:args.top_k]

    # Print Table
    header = f"{'FICHIER':<25} | {'NOM / CANDIDAT':<20} | {'SIMILARITÉ':<10} | {'VERDICT':<12} | {'DISTANCE':<8}"
    print(header)
    print("-" * len(header))

    for res in top_results:
        f_name = res["file"][:24]
        c_name = res["name"][:19]
        sim_str = f"{res['similarity']:.4f}"
        dist_str = f"{res['distance']:.4f}"
        print(f"{f_name:<25} | {c_name:<20} | {sim_str:<10} | {res['verdict']:<12} | {dist_str:<8}")

    print("=" * 80)
    print(f"IMPORTANT :\n{settings.DISCLAIMER}")
    print("=" * 80)

if __name__ == "__main__":
    main()
