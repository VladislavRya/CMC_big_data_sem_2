import json

import mrjob.job

import helpers
import similarity


WINDOW_SIZE = {
    'brand_model': 4,
    'model':       4,
    'title':       5,
}


class JSONLProtocol:
    @classmethod
    def read(cls, line):
        return (None, json.loads(line))

    @classmethod
    def write(cls, key, value):
        return json.dumps(value, ensure_ascii=False).encode('utf-8')


class SNMJob(mrjob.job.MRJob):
    INPUT_PROTOCOL = JSONLProtocol
    OUTPUT_PROTOCOL = JSONLProtocol
    SORT_VALUES = True

    def configure_args(self):
        super().configure_args()
        self.add_passthru_arg(
            '--pass-name',
            choices=sorted(helpers.SORT_KEYS),
            required=True,
            help='Which sort-key pass to run',
        )
        self.add_passthru_arg(
            '--threshold',
            type=float,
            default=similarity.THRESHOLD,
            help=f'Composite similarity threshold (default: {similarity.THRESHOLD})',
        )

    def mapper(self, _key, record):
        key_fn = helpers.SORT_KEYS[self.options.pass_name]
        bkv = key_fn(record)
        if not bkv:
            return
        yield helpers.partition_id(bkv), [bkv, record]

    def reducer(self, partition, items):
        pairs = sorted(items, key=lambda kv: kv[0])
        w = WINDOW_SIZE[self.options.pass_name]
        for i in range(len(pairs)):
            for j in range(i + 1, min(i + w, len(pairs))):
                a, b = pairs[i][1], pairs[j][1]
                res = similarity.score(a, b, threshold=self.options.threshold)
                if not res['matched']:
                    continue
                yield None, {
                    'a': a,
                    'b': b,
                    'score': res['score'],
                    'breakdown': res['breakdown'],
                    'reason': res['reason'],
                    'pass': self.options.pass_name,
                    'sort_keys': [pairs[i][0], pairs[j][0]],
                    'partition': partition,
                }


if __name__ == '__main__':
    SNMJob.run()
