# Import all agent implementations to trigger register_agent() calls
from . import intake  # noqa: F401
from . import planner  # noqa: F401
from . import doc_analyzer  # noqa: F401
from . import classifier  # noqa: F401
from . import compliance  # noqa: F401
from . import legal_lookup  # noqa: F401
from . import router  # noqa: F401
from . import consult  # noqa: F401
from . import summarizer  # noqa: F401
from . import drafter  # noqa: F401
from . import security_officer  # noqa: F401
