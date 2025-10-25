import io
import pandas as pd

class ReportService:
    def incidents_to_xlsx(self, incidents: list) -> bytes:
        df = pd.DataFrame(incidents)
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        return buf.getvalue()
