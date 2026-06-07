import json

import mrjob.job

from strategies import STRATEGIES


class JSONLProtocol:
    @classmethod
    def read(cls, line):
        return (None, json.loads(line))

    @classmethod
    def write(cls, key, value):
        return json.dumps(value, ensure_ascii=False).encode('utf-8')


class FuseJob(mrjob.job.MRJob):
    INPUT_PROTOCOL = JSONLProtocol
    OUTPUT_PROTOCOL = JSONLProtocol

    def configure_args(self):
        super().configure_args()
        self.add_passthru_arg(
            '--strategy',
            choices=sorted(STRATEGIES),
            required=True,
            help='Fusion strategy',
        )

    def mapper(self, _key, record):
        cluster_id = record.pop('_cluster_id')
        yield cluster_id, record

    def reducer_init(self):
        self.strategy = STRATEGIES[self.options.strategy]()

    def reducer(self, cluster_id, records_iter):
        records = list(records_iter)
        fused = self.strategy.fuse(records)
        fused['_cluster_id'] = cluster_id
        fused['_source_count'] = len(records)
        fused['_source_rec_ids'] = sorted(r['rec_id'] for r in records)
        yield None, fused


if __name__ == '__main__':
    FuseJob.run()
