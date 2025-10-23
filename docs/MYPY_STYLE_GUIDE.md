# Guide de Style Mypy - Emergence V8

**Date création** : 2025-10-23
**Auteur** : Claude Code (session MEGA cleanup 471→27 erreurs)
**Objectif** : Éviter régressions mypy + garder codebase type-safe à 95%+

---

## 📊 État Actuel

- **Résultat** : 471 → 27 erreurs (-444, -94.3%)
- **Fichiers refactorés** : 80+ backend Python
- **Erreurs restantes** : 27 triviales (cast + type:ignore)

---

## 🎯 Règles Obligatoires

### 1. Return Type Annotations

**TOUJOURS annoter les return types des fonctions publiques.**

```python
# ✅ BON
async def process_data() -> None:
    ...

async def get_data() -> dict[str, Any]:
    return {"key": "value"}

async def get_list() -> list[dict[str, Any]]:
    return [{"id": 1}]

async def redirect_user() -> RedirectResponse:
    return RedirectResponse(url="/home")

async def json_response() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})

# ❌ MAUVAIS
async def process_data():  # Missing return type
    ...
```

### 2. Types Modernes (Python 3.9+)

**Utiliser les types modernes natifs, PAS les typing anciens.**

```python
# ✅ BON
def process(data: dict[str, Any]) -> list[str]:
    ...

value: str | None = None
items: list[int] = []

# ❌ MAUVAIS
from typing import Dict, List, Union, Optional

def process(data: Dict[str, Any]) -> List[str]:  # Old style
    ...

value: Optional[str] = None  # Old style
```

### 3. Type Parameters Complets

**TOUJOURS spécifier les type parameters pour dict/list/set/tuple.**

```python
# ✅ BON
data: dict[str, Any] = {}
items: list[str] = []
pair: tuple[str, int] = ("a", 1)
unique: set[str] = set()
freq: Counter[str] = Counter()

# ❌ MAUVAIS
data: dict = {}  # Missing type params
items: list = []  # Missing type params
```

### 4. Cast pour no-any-return

**Utiliser `cast()` quand une fonction retourne `Any` mais on connaît le type.**

```python
from typing import cast

# ✅ BON
def get_value() -> float:
    result = some_dynamic_func()
    return cast(float, result)

def get_config() -> dict[str, Any]:
    raw = json.loads(text)
    return cast(dict[str, Any], raw)

# ❌ MAUVAIS
def get_value() -> float:
    return some_dynamic_func()  # Returning Any
```

### 5. Type:ignore Ciblés

**Toujours spécifier le code d'erreur exact dans `# type: ignore[code]`.**

```python
# ✅ BON
value = row["email"]  # type: ignore[no-redef]
return ""  # type: ignore[unreachable]
result = existing  # type: ignore[no-any-return]

# ❌ MAUVAIS
value = row["email"]  # type: ignore  # Too broad
```

### 6. Type Annotations Variadic

**Annoter *args et **kwargs avec `Any`.**

```python
# ✅ BON
def process(*args: Any, **kwargs: Any) -> None:
    ...

async def execute(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any
) -> T:
    ...

# ❌ MAUVAIS
def process(*args, **kwargs):  # Missing types
    ...
```

### 7. Import Any Systématique

**Dès qu'on utilise `dict`/`list` avec Any, importer `Any` de `typing`.**

```python
# ✅ BON
from typing import Any

def process(data: dict[str, Any]) -> list[Any]:
    ...

# ❌ MAUVAIS
# Oubli d'import Any
def process(data: dict[str, Any]) -> list[Any]:  # Name "Any" is not defined
    ...
```

---

## 🔧 Patterns Spécifiques

### FastAPI Endpoints

```python
from typing import Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter()

# ✅ BON
@router.get("/data")
async def get_data() -> dict[str, Any]:
    return {"key": "value"}

@router.post("/process")
async def process() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})

@router.get("/redirect")
async def redirect() -> RedirectResponse:
    return RedirectResponse(url="/home")

# ❌ MAUVAIS
@router.get("/data")
async def get_data():  # Missing return type
    return {"key": "value"}
```

### Dependency Injection FastAPI

```python
from fastapi import Depends
from typing import Any

# ✅ BON
async def get_data(
    user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    ...

# ❌ MAUVAIS
async def get_data(
    user: dict = Depends(get_current_user)  # Missing type params
):  # Missing return type
    ...
```

### Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Any

# ✅ BON
class UserModel(BaseModel):
    id: str
    email: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = []

# ❌ MAUVAIS
class UserModel(BaseModel):
    metadata: dict = {}  # Missing type params
    tags: list = []  # Missing type params
```

### Collections (Counter, defaultdict, etc.)

```python
from collections import Counter, defaultdict
from typing import Any

# ✅ BON
freq: Counter[str] = Counter()
data: defaultdict[str, list[Any]] = defaultdict(list)

# ❌ MAUVAIS
freq: Counter = Counter()  # Missing type params
data: defaultdict = defaultdict(list)  # Missing type params
```

### Conditional Assignments (no-redef)

```python
# ✅ BON
if PROMETHEUS_AVAILABLE:
    metric: Gauge = Gauge(...)
else:
    metric: Gauge | None = None  # type: ignore[no-redef]

# ❌ MAUVAIS
if PROMETHEUS_AVAILABLE:
    metric = Gauge(...)
else:
    metric = None  # Redefinition error
```

---

## ⚠️ Erreurs Fréquentes

### 1. Oublier Return Type

```python
# ❌ ERREUR : Function is missing a return type annotation
def process():
    return None

# ✅ FIX
def process() -> None:
    return None
```

### 2. Type Parameters Manquants

```python
# ❌ ERREUR : Missing type parameters for generic type "dict"
def get_config() -> dict:
    return {}

# ✅ FIX
def get_config() -> dict[str, Any]:
    return {}
```

### 3. Returning Any

```python
# ❌ ERREUR : Returning Any from function declared to return "float"
def get_value() -> float:
    return json.loads(text)["value"]

# ✅ FIX
def get_value() -> float:
    return cast(float, json.loads(text)["value"])
```

### 4. Name "Any" Not Defined

```python
# ❌ ERREUR : Name "Any" is not defined
def process(data: dict[str, Any]) -> None:
    ...

# ✅ FIX
from typing import Any

def process(data: dict[str, Any]) -> None:
    ...
```

---

## 🚀 Workflow Recommandé

### Avant Commit

```bash
# 1. Check mypy
mypy src/backend/ --no-error-summary

# 2. Si erreurs, fixer en priorité :
#    - Missing return type annotations
#    - Missing type parameters
#    - Name "Any" is not defined

# 3. Check ruff
ruff check src/backend/

# 4. Commit
git add . && git commit -m "fix(types): ..."
```

### Ajout Nouveau Module

```python
"""
Nouveau module - Template type-safe
"""
from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

class MyService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def process(self, data: dict[str, Any]) -> None:
        ...

    async def get_data(self) -> list[dict[str, Any]]:
        return []
```

---

## 📈 Maintenance

### Pre-commit Hook (TODO P1.3)

**Actuellement** : Mypy warnings only (permet commits avec erreurs)
**Objectif** : Mypy strict mode (bloque commits avec erreurs)

```bash
# .git/hooks/pre-commit
#!/bin/bash
mypy src/backend/ --no-error-summary
if [ $? -ne 0 ]; then
    echo "❌ Mypy errors detected. Fix before commit."
    exit 1
fi
```

### Objectif Long Terme

- **Maintenir 95%+** type coverage
- **0 erreurs mypy** sur code critique (core/*, features/chat/*, features/memory/*)
- **<10 erreurs** au total sur tout le backend

---

## 📚 Ressources

- [Mypy Docs](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [Python 3.9+ Type Hints](https://docs.python.org/3/library/typing.html)

---

**Dernière mise à jour** : 2025-10-23 (Session MEGA cleanup 471→27)
