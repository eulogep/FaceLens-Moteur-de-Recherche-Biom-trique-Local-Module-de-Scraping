# FaceLens — Procédure d'exploitation

## Avant toute modification majeure

Lancer une sauvegarde SQLite/FAISS :

```powershell
.\.venv\Scripts\python.exe scripts\backup.py
```

Le script conserve automatiquement les cinq sauvegardes les plus récentes.

## Maintenance mensuelle

1. Vérifier les mises à jour sans les appliquer :

   ```powershell
   .\.venv\Scripts\python.exe -m pip list --outdated
   ```

2. Auditer les vulnérabilités sans correction automatique :

   ```powershell
   .\tmp\audit-step2-venv\Scripts\python.exe -m pip_audit -r requirements.txt
   ```

3. Vérifier l'intégrité SQLite/FAISS :

   ```python
   from core.db import DatabaseManager
   from core.vector_index import VectorIndexManager

   db = DatabaseManager()
   idx = VectorIndexManager()
   print(f"SQLite: {db.count_faces()} | FAISS: {idx.ntotal}")
   assert db.verify_integrity(idx)
   ```

4. Exécuter les tests avec un répertoire temporaire contrôlé :

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests\ -v --basetemp=D:/OSINT/tmp/pytest
   ```

5. Exécuter la validation E2E sans écraser un ancien rapport :

   ```powershell
   .\.venv\Scripts\python.exe scripts\e2e_validation.py
   ```

Ne jamais mettre à jour InsightFace ou ONNX Runtime sans une
revalidation buffalo_l complète à 30/30 sur LFW.
