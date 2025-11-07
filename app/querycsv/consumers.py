
import json
from channels.consumer import SyncConsumer
from asgiref.sync import async_to_sync, sync_to_async
from core.abstracts.admin import AdminBase
from core.abstracts.consumers import ConsumerAllowAny, ConsumerBase
from querycsv.models import QueryCsvUploadJob
from querycsv.services import QueryCsvService



class QueryCsvConsumer(ConsumerBase):

    permission_classes = [ConsumerAllowAny]

    async def _get_job_logs(self):

        job_id = self.scope["url_route"]["kwargs"]["job_id"]
        service = await QueryCsvUploadJob.objects.aget(id=job_id)
        #self.job = await sync_to_async(service._get_job)()

        def _get_logs():
            return service.logs
        
        def _get_logs_html():
            try:
                renderer = AdminBase()
                return str(renderer.as_json(service.logs))
            except Exception:
                # Fallback to raw json string
                return json.dumps(service.logs or {})
        
        service = await sync_to_async(_get_logs_html)()
        return service

    async def connect(self):
        connected = await super().connect()
        if not connected:
            return
        
        self.job_id = self.scope["url_route"]["kwargs"]["job_id"]
        self.group_name = f"job_{self.job_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        current_job_log = await self._get_job_logs()


        await self.send_json({
            "type" : "initial_job_log",
            "data" : current_job_log
        })

    async def job_update(self, event):
        """Fires when job update occurs"""

        current_job_log = await self._get_job_logs()
        
        await self.send_json({
            "type" : "initial_job_log",
            "data" : current_job_log
        })


