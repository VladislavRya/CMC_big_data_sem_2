import json

import mrjob.job

from transformers import TRANSFORMERS


class JSONLProtocol:
    @classmethod
    def read(cls, line):
        return (None, json.loads(line))

    @classmethod
    def write(cls, key, value):
        return json.dumps(value, ensure_ascii=False).encode('utf-8')


class TransformJob(mrjob.job.MRJob):
    INPUT_PROTOCOL = JSONLProtocol
    OUTPUT_PROTOCOL = JSONLProtocol

    def configure_args(self):
        super().configure_args()
        self.add_passthru_arg(
            '--source',
            choices=sorted(TRANSFORMERS.keys()),
            required=True,
            help='Source marketplace',
        )

    def mapper_init(self):
        self.transformer = TRANSFORMERS[self.options.source]()

    def mapper(self, _key, record):
        yield None, self.transformer.transform(record)


if __name__ == '__main__':
    TransformJob.run()
