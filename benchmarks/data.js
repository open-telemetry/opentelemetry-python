window.BENCHMARK_DATA = {
  "lastUpdate": 1703699705019,
  "repoUrl": "https://github.com/open-telemetry/opentelemetry-python",
  "entries": {
    "OpenTelemetry Python SDK Benchmarks - Python 3.11 - SDK": [
      {
        "commit": {
          "author": {
            "email": "ocelotl@users.noreply.github.com",
            "name": "Diego Hurtado",
            "username": "ocelotl"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "48fdb6389a78d7c357565268a68d1705706f453f",
          "message": "Rename benchmarks branch to gh-pages (#3581)\n\nFixes #3580",
          "timestamp": "2023-12-14T20:33:34-06:00",
          "tree_id": "bbcc7db43bfb09d8be31cc43593ce6278e8ea718",
          "url": "https://github.com/open-telemetry/opentelemetry-python/commit/48fdb6389a78d7c357565268a68d1705706f453f"
        },
        "date": 1702628043216,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-delta]",
            "value": 919125.7789501001,
            "unit": "iter/sec",
            "range": "stddev: 8.963932919490788e-8",
            "extra": "mean: 1.0879903740076586 usec\nrounds: 30806"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-delta]",
            "value": 866171.2563752028,
            "unit": "iter/sec",
            "range": "stddev: 3.360539114209923e-7",
            "extra": "mean: 1.15450610100461 usec\nrounds: 97154"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-delta]",
            "value": 767111.585345143,
            "unit": "iter/sec",
            "range": "stddev: 2.552029932275722e-7",
            "extra": "mean: 1.3035913146195994 usec\nrounds: 112035"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-delta]",
            "value": 678826.2398825133,
            "unit": "iter/sec",
            "range": "stddev: 2.1136217014928756e-7",
            "extra": "mean: 1.473131033021165 usec\nrounds: 78755"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-delta]",
            "value": 562677.4826108214,
            "unit": "iter/sec",
            "range": "stddev: 2.518112170502371e-7",
            "extra": "mean: 1.77721702201411 usec\nrounds: 90642"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-cumulative]",
            "value": 919666.2959146053,
            "unit": "iter/sec",
            "range": "stddev: 1.7469742198275074e-7",
            "extra": "mean: 1.0873509276595845 usec\nrounds: 53090"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-cumulative]",
            "value": 870348.3592292825,
            "unit": "iter/sec",
            "range": "stddev: 1.711390158127123e-7",
            "extra": "mean: 1.148965226849543 usec\nrounds: 137466"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-cumulative]",
            "value": 769770.9552563041,
            "unit": "iter/sec",
            "range": "stddev: 2.476861853944945e-7",
            "extra": "mean: 1.299087726253634 usec\nrounds: 134673"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-cumulative]",
            "value": 673820.8875513654,
            "unit": "iter/sec",
            "range": "stddev: 3.095565818301746e-7",
            "extra": "mean: 1.4840739111456678 usec\nrounds: 124956"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-cumulative]",
            "value": 561086.0291710411,
            "unit": "iter/sec",
            "range": "stddev: 3.556652894969962e-7",
            "extra": "mean: 1.7822578856176807 usec\nrounds: 84222"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[0]",
            "value": 922689.0368297382,
            "unit": "iter/sec",
            "range": "stddev: 3.541918042448067e-7",
            "extra": "mean: 1.0837887523145326 usec\nrounds: 32110"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[1]",
            "value": 879613.799238098,
            "unit": "iter/sec",
            "range": "stddev: 2.743127584021781e-7",
            "extra": "mean: 1.1368625649872455 usec\nrounds: 117272"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[3]",
            "value": 779263.9971320797,
            "unit": "iter/sec",
            "range": "stddev: 2.4385131154992634e-7",
            "extra": "mean: 1.2832621597819143 usec\nrounds: 117645"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[5]",
            "value": 684313.1006268384,
            "unit": "iter/sec",
            "range": "stddev: 2.2714819341457625e-7",
            "extra": "mean: 1.4613193859418867 usec\nrounds: 112800"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[10]",
            "value": 559370.3746652022,
            "unit": "iter/sec",
            "range": "stddev: 2.954817015959684e-7",
            "extra": "mean: 1.7877242794606811 usec\nrounds: 115556"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[0]",
            "value": 747351.1299360996,
            "unit": "iter/sec",
            "range": "stddev: 1.1132106793108436e-7",
            "extra": "mean: 1.338059126351361 usec\nrounds: 3834"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[1]",
            "value": 745559.9194552418,
            "unit": "iter/sec",
            "range": "stddev: 2.473517316198177e-7",
            "extra": "mean: 1.3412738183815862 usec\nrounds: 198805"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[3]",
            "value": 742225.8500105082,
            "unit": "iter/sec",
            "range": "stddev: 1.9785063942307618e-7",
            "extra": "mean: 1.3472988039770406 usec\nrounds: 159404"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[5]",
            "value": 796165.5373182931,
            "unit": "iter/sec",
            "range": "stddev: 1.0563073921687926e-7",
            "extra": "mean: 1.256020203246021 usec\nrounds: 176487"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[7]",
            "value": 794434.4275364181,
            "unit": "iter/sec",
            "range": "stddev: 1.1516120695892894e-7",
            "extra": "mean: 1.2587571300265161 usec\nrounds: 172656"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[0]",
            "value": 737451.5779110143,
            "unit": "iter/sec",
            "range": "stddev: 2.545714008506206e-7",
            "extra": "mean: 1.356021235770773 usec\nrounds: 19623"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[1]",
            "value": 792052.4711555769,
            "unit": "iter/sec",
            "range": "stddev: 1.082930509297308e-7",
            "extra": "mean: 1.2625426173357364 usec\nrounds: 185833"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[3]",
            "value": 746007.1395119943,
            "unit": "iter/sec",
            "range": "stddev: 2.3346138161175505e-7",
            "extra": "mean: 1.3404697449064051 usec\nrounds: 180461"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[5]",
            "value": 748729.2809081713,
            "unit": "iter/sec",
            "range": "stddev: 2.571548644077778e-7",
            "extra": "mean: 1.3355962234935568 usec\nrounds: 190482"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[7]",
            "value": 794174.2094031352,
            "unit": "iter/sec",
            "range": "stddev: 1.1371529190980426e-7",
            "extra": "mean: 1.2591695728215022 usec\nrounds: 182145"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[0]",
            "value": 725520.3123605299,
            "unit": "iter/sec",
            "range": "stddev: 1.6657516286637725e-7",
            "extra": "mean: 1.3783211620174103 usec\nrounds: 29187"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[1]",
            "value": 770948.2963728677,
            "unit": "iter/sec",
            "range": "stddev: 1.1249219846066901e-7",
            "extra": "mean: 1.297103845620734 usec\nrounds: 173689"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[3]",
            "value": 771659.964464329,
            "unit": "iter/sec",
            "range": "stddev: 1.0792565280216183e-7",
            "extra": "mean: 1.2959075837168514 usec\nrounds: 176516"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[5]",
            "value": 773619.7946507485,
            "unit": "iter/sec",
            "range": "stddev: 1.0863703105812781e-7",
            "extra": "mean: 1.2926246289386263 usec\nrounds: 173942"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[7]",
            "value": 723549.583472139,
            "unit": "iter/sec",
            "range": "stddev: 2.3658190943851145e-7",
            "extra": "mean: 1.3820752894379988 usec\nrounds: 198547"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[0]",
            "value": 720717.3906254729,
            "unit": "iter/sec",
            "range": "stddev: 2.499081775138413e-7",
            "extra": "mean: 1.3875064109833015 usec\nrounds: 29166"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[1]",
            "value": 720605.6629638305,
            "unit": "iter/sec",
            "range": "stddev: 2.2854935390789634e-7",
            "extra": "mean: 1.3877215395269424 usec\nrounds: 198108"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[3]",
            "value": 770908.6440664794,
            "unit": "iter/sec",
            "range": "stddev: 1.1127458966978588e-7",
            "extra": "mean: 1.297170563200696 usec\nrounds: 179586"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[5]",
            "value": 776138.9971991688,
            "unit": "iter/sec",
            "range": "stddev: 1.0976382706871773e-7",
            "extra": "mean: 1.2884290102786644 usec\nrounds: 179166"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[7]",
            "value": 726078.7546180703,
            "unit": "iter/sec",
            "range": "stddev: 2.484948283955935e-7",
            "extra": "mean: 1.3772610665712384 usec\nrounds: 194943"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[0]",
            "value": 698478.4011960655,
            "unit": "iter/sec",
            "range": "stddev: 3.018679547085174e-7",
            "extra": "mean: 1.431683496995201 usec\nrounds: 26481"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[1]",
            "value": 696636.6460634929,
            "unit": "iter/sec",
            "range": "stddev: 2.3764951840852628e-7",
            "extra": "mean: 1.4354685554524476 usec\nrounds: 191160"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[3]",
            "value": 689228.0590736185,
            "unit": "iter/sec",
            "range": "stddev: 2.185035319096884e-7",
            "extra": "mean: 1.4508985622902317 usec\nrounds: 199952"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[5]",
            "value": 682303.9362160373,
            "unit": "iter/sec",
            "range": "stddev: 2.5268452712937975e-7",
            "extra": "mean: 1.4656224988908328 usec\nrounds: 193433"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[7]",
            "value": 681694.5013493592,
            "unit": "iter/sec",
            "range": "stddev: 2.4945746354848175e-7",
            "extra": "mean: 1.4669327653671562 usec\nrounds: 169414"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 66727.45592804764,
            "unit": "iter/sec",
            "range": "stddev: 0.000007420231283133922",
            "extra": "mean: 14.986334876580672 usec\nrounds: 33"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 59365.31338844127,
            "unit": "iter/sec",
            "range": "stddev: 9.421017812330877e-7",
            "extra": "mean: 16.84485338191957 usec\nrounds: 23564"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ocelotl@users.noreply.github.com",
            "name": "Diego Hurtado",
            "username": "ocelotl"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "48fdb6389a78d7c357565268a68d1705706f453f",
          "message": "Rename benchmarks branch to gh-pages (#3581)\n\nFixes #3580",
          "timestamp": "2023-12-14T20:33:34-06:00",
          "tree_id": "bbcc7db43bfb09d8be31cc43593ce6278e8ea718",
          "url": "https://github.com/open-telemetry/opentelemetry-python/commit/48fdb6389a78d7c357565268a68d1705706f453f"
        },
        "date": 1702628099034,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-delta]",
            "value": 914534.7312585397,
            "unit": "iter/sec",
            "range": "stddev: 1.1270452849354733e-7",
            "extra": "mean: 1.0934521848326602 usec\nrounds: 32586"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-delta]",
            "value": 864052.3903774832,
            "unit": "iter/sec",
            "range": "stddev: 8.546812213871608e-8",
            "extra": "mean: 1.1573372299370928 usec\nrounds: 90819"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-delta]",
            "value": 761308.7564849785,
            "unit": "iter/sec",
            "range": "stddev: 1.3596579167115952e-7",
            "extra": "mean: 1.3135275162433142 usec\nrounds: 126012"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-delta]",
            "value": 674780.8249785887,
            "unit": "iter/sec",
            "range": "stddev: 1.1661564999311933e-7",
            "extra": "mean: 1.4819626802995338 usec\nrounds: 115494"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-delta]",
            "value": 557321.5960060655,
            "unit": "iter/sec",
            "range": "stddev: 1.4991253600321297e-7",
            "extra": "mean: 1.7942961607199532 usec\nrounds: 111628"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-cumulative]",
            "value": 910859.0629007356,
            "unit": "iter/sec",
            "range": "stddev: 7.865002129585527e-8",
            "extra": "mean: 1.097864687008092 usec\nrounds: 51146"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-cumulative]",
            "value": 858930.9927815739,
            "unit": "iter/sec",
            "range": "stddev: 1.4259343754750532e-7",
            "extra": "mean: 1.1642378822093569 usec\nrounds: 145258"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-cumulative]",
            "value": 779896.0115615657,
            "unit": "iter/sec",
            "range": "stddev: 1.6928876395082407e-7",
            "extra": "mean: 1.282222226008985 usec\nrounds: 124104"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-cumulative]",
            "value": 672149.6392529444,
            "unit": "iter/sec",
            "range": "stddev: 1.0159950706515345e-7",
            "extra": "mean: 1.4877639465989188 usec\nrounds: 49617"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-cumulative]",
            "value": 564166.4704047614,
            "unit": "iter/sec",
            "range": "stddev: 1.6222781776513107e-7",
            "extra": "mean: 1.7725264659605697 usec\nrounds: 118685"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[0]",
            "value": 926062.2100203916,
            "unit": "iter/sec",
            "range": "stddev: 7.712626534427721e-8",
            "extra": "mean: 1.0798410616258494 usec\nrounds: 25179"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[1]",
            "value": 880042.8530710989,
            "unit": "iter/sec",
            "range": "stddev: 1.7188413823432172e-7",
            "extra": "mean: 1.1363083019313036 usec\nrounds: 48492"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[3]",
            "value": 774632.1206254049,
            "unit": "iter/sec",
            "range": "stddev: 3.476839558201053e-7",
            "extra": "mean: 1.290935365800017 usec\nrounds: 126860"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[5]",
            "value": 679741.4626742263,
            "unit": "iter/sec",
            "range": "stddev: 1.3977711367002874e-7",
            "extra": "mean: 1.4711475684678974 usec\nrounds: 112611"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[10]",
            "value": 560431.0746659256,
            "unit": "iter/sec",
            "range": "stddev: 1.864216601025188e-7",
            "extra": "mean: 1.784340742697222 usec\nrounds: 122770"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[0]",
            "value": 752937.0015770134,
            "unit": "iter/sec",
            "range": "stddev: 1.5148459533567995e-7",
            "extra": "mean: 1.328132364202473 usec\nrounds: 3985"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[1]",
            "value": 748368.5073086824,
            "unit": "iter/sec",
            "range": "stddev: 1.78901080051197e-7",
            "extra": "mean: 1.3362400879163747 usec\nrounds: 180522"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[3]",
            "value": 741997.8063398638,
            "unit": "iter/sec",
            "range": "stddev: 2.7695012813972453e-7",
            "extra": "mean: 1.3477128792776527 usec\nrounds: 156022"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[5]",
            "value": 805447.9002434706,
            "unit": "iter/sec",
            "range": "stddev: 7.40235212877754e-8",
            "extra": "mean: 1.241545231786836 usec\nrounds: 182052"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[7]",
            "value": 803271.7818976644,
            "unit": "iter/sec",
            "range": "stddev: 8.62684285899718e-8",
            "extra": "mean: 1.2449086629653305 usec\nrounds: 187227"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[0]",
            "value": 734621.2431827871,
            "unit": "iter/sec",
            "range": "stddev: 7.63558221705793e-7",
            "extra": "mean: 1.3612456885502586 usec\nrounds: 20213"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[1]",
            "value": 797356.9606610265,
            "unit": "iter/sec",
            "range": "stddev: 1.0116884351975274e-7",
            "extra": "mean: 1.2541434380543663 usec\nrounds: 187292"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[3]",
            "value": 796386.5407922904,
            "unit": "iter/sec",
            "range": "stddev: 9.123947390869153e-8",
            "extra": "mean: 1.2556716478472167 usec\nrounds: 189741"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[5]",
            "value": 793398.1494794333,
            "unit": "iter/sec",
            "range": "stddev: 9.801316521611751e-8",
            "extra": "mean: 1.2604012256092643 usec\nrounds: 182021"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[7]",
            "value": 801066.9017777751,
            "unit": "iter/sec",
            "range": "stddev: 1.0337396732053723e-7",
            "extra": "mean: 1.2483351862132124 usec\nrounds: 186414"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[0]",
            "value": 732744.2461842541,
            "unit": "iter/sec",
            "range": "stddev: 1.415993881433974e-7",
            "extra": "mean: 1.3647326542753124 usec\nrounds: 29331"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[1]",
            "value": 731715.1335620825,
            "unit": "iter/sec",
            "range": "stddev: 1.5709926475976624e-7",
            "extra": "mean: 1.3666520673583347 usec\nrounds: 196909"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[3]",
            "value": 787579.0228127004,
            "unit": "iter/sec",
            "range": "stddev: 9.717123658903031e-8",
            "extra": "mean: 1.2697138585899297 usec\nrounds: 182362"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[5]",
            "value": 788881.0130716665,
            "unit": "iter/sec",
            "range": "stddev: 9.360788151980771e-8",
            "extra": "mean: 1.267618288981629 usec\nrounds: 185898"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[7]",
            "value": 785532.557949987,
            "unit": "iter/sec",
            "range": "stddev: 9.39930708399454e-8",
            "extra": "mean: 1.273021709768098 usec\nrounds: 186998"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[0]",
            "value": 733727.0911390329,
            "unit": "iter/sec",
            "range": "stddev: 1.1502981571529203e-7",
            "extra": "mean: 1.362904562304776 usec\nrounds: 27704"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[1]",
            "value": 788707.8045534155,
            "unit": "iter/sec",
            "range": "stddev: 1.0113338676892568e-7",
            "extra": "mean: 1.2678966712726052 usec\nrounds: 186706"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[3]",
            "value": 786170.3684120289,
            "unit": "iter/sec",
            "range": "stddev: 9.633345785417816e-8",
            "extra": "mean: 1.2719889227316996 usec\nrounds: 183797"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[5]",
            "value": 787354.8352420579,
            "unit": "iter/sec",
            "range": "stddev: 1.038557743004313e-7",
            "extra": "mean: 1.2700753907132203 usec\nrounds: 183233"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[7]",
            "value": 785749.3036353132,
            "unit": "iter/sec",
            "range": "stddev: 9.951380770357785e-8",
            "extra": "mean: 1.272670552011238 usec\nrounds: 181315"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[0]",
            "value": 702034.7010578095,
            "unit": "iter/sec",
            "range": "stddev: 1.5831219165612887e-7",
            "extra": "mean: 1.4244310124459991 usec\nrounds: 25289"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[1]",
            "value": 702972.9199753063,
            "unit": "iter/sec",
            "range": "stddev: 1.656699058252965e-7",
            "extra": "mean: 1.4225299034778291 usec\nrounds: 188013"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[3]",
            "value": 730412.8132781805,
            "unit": "iter/sec",
            "range": "stddev: 1.104800999248017e-7",
            "extra": "mean: 1.3690887972130168 usec\nrounds: 113841"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[5]",
            "value": 695306.13278008,
            "unit": "iter/sec",
            "range": "stddev: 1.7800481340548361e-7",
            "extra": "mean: 1.4382154174329604 usec\nrounds: 199915"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[7]",
            "value": 735978.4984264297,
            "unit": "iter/sec",
            "range": "stddev: 9.046722847968993e-8",
            "extra": "mean: 1.3587353463967569 usec\nrounds: 166317"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 72891.64451978673,
            "unit": "iter/sec",
            "range": "stddev: 0.000004170946460692756",
            "extra": "mean: 13.718993536063602 usec\nrounds: 35"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 58711.63452041671,
            "unit": "iter/sec",
            "range": "stddev: 0.0000011305844337584604",
            "extra": "mean: 17.032399253886457 usec\nrounds: 17920"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "107717825+opentelemetrybot@users.noreply.github.com",
            "name": "OpenTelemetry Bot",
            "username": "opentelemetrybot"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "bede4d259aa497bd2d62d1dd249c0b43dc4067a2",
          "message": "Update version to 1.23.0.dev/0.44b0.dev (#3582)\n\n* Update version to 1.23.0.dev/0.44b0.dev\r\n\r\n* Update SHA\r\n\r\n---------\r\n\r\nCo-authored-by: Diego Hurtado <ocelotl@users.noreply.github.com>",
          "timestamp": "2023-12-15T16:54:07-06:00",
          "tree_id": "c9bd56dc2412b8efcec819b34a70a5da26f7e702",
          "url": "https://github.com/open-telemetry/opentelemetry-python/commit/bede4d259aa497bd2d62d1dd249c0b43dc4067a2"
        },
        "date": 1702681333220,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-delta]",
            "value": 905308.1331150084,
            "unit": "iter/sec",
            "range": "stddev: 7.556850574762745e-8",
            "extra": "mean: 1.1045962843161183 usec\nrounds: 30510"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-delta]",
            "value": 856950.8506421865,
            "unit": "iter/sec",
            "range": "stddev: 1.5161336459879368e-7",
            "extra": "mean: 1.1669280674038827 usec\nrounds: 92652"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-delta]",
            "value": 770199.6988840349,
            "unit": "iter/sec",
            "range": "stddev: 1.3609628784708595e-7",
            "extra": "mean: 1.2983645688889902 usec\nrounds: 114131"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-delta]",
            "value": 658741.731199525,
            "unit": "iter/sec",
            "range": "stddev: 1.4791268163190647e-7",
            "extra": "mean: 1.518045620366371 usec\nrounds: 114582"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-delta]",
            "value": 565109.7944386901,
            "unit": "iter/sec",
            "range": "stddev: 1.4878302430341927e-7",
            "extra": "mean: 1.769567630646494 usec\nrounds: 101488"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-cumulative]",
            "value": 904906.8582893085,
            "unit": "iter/sec",
            "range": "stddev: 1.399887154910223e-7",
            "extra": "mean: 1.1050861100671303 usec\nrounds: 54091"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-cumulative]",
            "value": 851206.0992502259,
            "unit": "iter/sec",
            "range": "stddev: 1.3219748459348296e-7",
            "extra": "mean: 1.174803612052166 usec\nrounds: 129868"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-cumulative]",
            "value": 764983.5041132035,
            "unit": "iter/sec",
            "range": "stddev: 1.5139796843739797e-7",
            "extra": "mean: 1.3072177303473178 usec\nrounds: 120389"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-cumulative]",
            "value": 672441.0715164668,
            "unit": "iter/sec",
            "range": "stddev: 1.574051768804397e-7",
            "extra": "mean: 1.4871191578837282 usec\nrounds: 132807"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-cumulative]",
            "value": 563617.020189557,
            "unit": "iter/sec",
            "range": "stddev: 1.6179391385845005e-7",
            "extra": "mean: 1.7742544390580641 usec\nrounds: 101450"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[0]",
            "value": 906468.5610555597,
            "unit": "iter/sec",
            "range": "stddev: 1.1413817640303006e-7",
            "extra": "mean: 1.1031822205014208 usec\nrounds: 32305"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[1]",
            "value": 860080.632323997,
            "unit": "iter/sec",
            "range": "stddev: 1.455004789814918e-7",
            "extra": "mean: 1.1626816863646043 usec\nrounds: 132300"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[3]",
            "value": 773443.3011584639,
            "unit": "iter/sec",
            "range": "stddev: 1.3230722992287964e-7",
            "extra": "mean: 1.2929195954017563 usec\nrounds: 118830"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[5]",
            "value": 667571.6608740188,
            "unit": "iter/sec",
            "range": "stddev: 1.5983302579549585e-7",
            "extra": "mean: 1.4979665234601918 usec\nrounds: 118633"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[10]",
            "value": 570811.099189765,
            "unit": "iter/sec",
            "range": "stddev: 1.9008839639820338e-7",
            "extra": "mean: 1.7518930543212017 usec\nrounds: 120863"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[0]",
            "value": 754987.3093988054,
            "unit": "iter/sec",
            "range": "stddev: 1.1062843879945223e-7",
            "extra": "mean: 1.3245255748686657 usec\nrounds: 3884"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[1]",
            "value": 808416.9853264663,
            "unit": "iter/sec",
            "range": "stddev: 7.093354199779901e-8",
            "extra": "mean: 1.236985390152541 usec\nrounds: 188211"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[3]",
            "value": 753169.1830183465,
            "unit": "iter/sec",
            "range": "stddev: 1.7389970252950374e-7",
            "extra": "mean: 1.3277229373518338 usec\nrounds: 165676"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[5]",
            "value": 805198.7821379004,
            "unit": "iter/sec",
            "range": "stddev: 7.271449959700598e-8",
            "extra": "mean: 1.2419293498493365 usec\nrounds: 187325"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[7]",
            "value": 800147.9443816785,
            "unit": "iter/sec",
            "range": "stddev: 6.858447445622628e-8",
            "extra": "mean: 1.249768879644825 usec\nrounds: 188277"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[0]",
            "value": 747797.3921633464,
            "unit": "iter/sec",
            "range": "stddev: 1.3263455598197535e-7",
            "extra": "mean: 1.3372606142782097 usec\nrounds: 19105"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[1]",
            "value": 795250.6077206717,
            "unit": "iter/sec",
            "range": "stddev: 6.701491241031224e-8",
            "extra": "mean: 1.2574652446556138 usec\nrounds: 185416"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[3]",
            "value": 744411.5272373363,
            "unit": "iter/sec",
            "range": "stddev: 1.3615492391186128e-7",
            "extra": "mean: 1.3433429808794135 usec\nrounds: 189073"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[5]",
            "value": 808098.1750487215,
            "unit": "iter/sec",
            "range": "stddev: 6.570040913883513e-8",
            "extra": "mean: 1.2374734046883702 usec\nrounds: 189073"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[7]",
            "value": 808838.90626489,
            "unit": "iter/sec",
            "range": "stddev: 6.484894470733388e-8",
            "extra": "mean: 1.2363401318290517 usec\nrounds: 183860"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[0]",
            "value": 744253.4164179937,
            "unit": "iter/sec",
            "range": "stddev: 1.1653613158217852e-7",
            "extra": "mean: 1.3436283635927198 usec\nrounds: 26580"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[1]",
            "value": 782436.3825024822,
            "unit": "iter/sec",
            "range": "stddev: 8.90224697765778e-8",
            "extra": "mean: 1.2780591781809527 usec\nrounds: 182455"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[3]",
            "value": 792029.120145708,
            "unit": "iter/sec",
            "range": "stddev: 6.274657721347842e-8",
            "extra": "mean: 1.2625798402665196 usec\nrounds: 181591"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[5]",
            "value": 796077.6438653194,
            "unit": "iter/sec",
            "range": "stddev: 6.651646853261294e-8",
            "extra": "mean: 1.2561588781020714 usec\nrounds: 182796"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[7]",
            "value": 739044.5123107713,
            "unit": "iter/sec",
            "range": "stddev: 1.3828124320878338e-7",
            "extra": "mean: 1.3530984715295415 usec\nrounds: 194943"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[0]",
            "value": 739397.9956322442,
            "unit": "iter/sec",
            "range": "stddev: 1.3120984420018873e-7",
            "extra": "mean: 1.3524515969845448 usec\nrounds: 27545"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[1]",
            "value": 786250.6829079884,
            "unit": "iter/sec",
            "range": "stddev: 7.069300617419416e-8",
            "extra": "mean: 1.2718589906993134 usec\nrounds: 180613"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[3]",
            "value": 782876.3930886254,
            "unit": "iter/sec",
            "range": "stddev: 6.613020795024621e-8",
            "extra": "mean: 1.2773408533303356 usec\nrounds: 188409"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[5]",
            "value": 792386.4718647426,
            "unit": "iter/sec",
            "range": "stddev: 6.01891157911864e-8",
            "extra": "mean: 1.2620104399898138 usec\nrounds: 184905"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[7]",
            "value": 737083.2467720362,
            "unit": "iter/sec",
            "range": "stddev: 1.7368119981817074e-7",
            "extra": "mean: 1.3566988591578697 usec\nrounds: 193154"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[0]",
            "value": 703976.016508479,
            "unit": "iter/sec",
            "range": "stddev: 1.39140479449587e-7",
            "extra": "mean: 1.4205029383809349 usec\nrounds: 26273"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[1]",
            "value": 735228.5087388803,
            "unit": "iter/sec",
            "range": "stddev: 1.5343286193549984e-7",
            "extra": "mean: 1.3601213610653862 usec\nrounds: 170897"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[3]",
            "value": 704386.6018471706,
            "unit": "iter/sec",
            "range": "stddev: 1.5390460162933538e-7",
            "extra": "mean: 1.4196749304680387 usec\nrounds: 147655"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[5]",
            "value": 722299.0477029216,
            "unit": "iter/sec",
            "range": "stddev: 7.28986845155812e-8",
            "extra": "mean: 1.384468113560764 usec\nrounds: 165014"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[7]",
            "value": 735112.6376136775,
            "unit": "iter/sec",
            "range": "stddev: 7.555833415889221e-8",
            "extra": "mean: 1.3603357483367442 usec\nrounds: 163556"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 72377.52183980968,
            "unit": "iter/sec",
            "range": "stddev: 0.000003881946948597333",
            "extra": "mean: 13.816444312824924 usec\nrounds: 34"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 59717.4152689886,
            "unit": "iter/sec",
            "range": "stddev: 5.619429924719815e-7",
            "extra": "mean: 16.745533869737034 usec\nrounds: 26126"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "107717825+opentelemetrybot@users.noreply.github.com",
            "name": "OpenTelemetry Bot",
            "username": "opentelemetrybot"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "bede4d259aa497bd2d62d1dd249c0b43dc4067a2",
          "message": "Update version to 1.23.0.dev/0.44b0.dev (#3582)\n\n* Update version to 1.23.0.dev/0.44b0.dev\r\n\r\n* Update SHA\r\n\r\n---------\r\n\r\nCo-authored-by: Diego Hurtado <ocelotl@users.noreply.github.com>",
          "timestamp": "2023-12-15T16:54:07-06:00",
          "tree_id": "c9bd56dc2412b8efcec819b34a70a5da26f7e702",
          "url": "https://github.com/open-telemetry/opentelemetry-python/commit/bede4d259aa497bd2d62d1dd249c0b43dc4067a2"
        },
        "date": 1702681386666,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-delta]",
            "value": 896122.6769966929,
            "unit": "iter/sec",
            "range": "stddev: 2.059917603507713e-7",
            "extra": "mean: 1.115918641130081 usec\nrounds: 31959"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-delta]",
            "value": 851229.0914252552,
            "unit": "iter/sec",
            "range": "stddev: 2.3571817585237875e-7",
            "extra": "mean: 1.1747718799479119 usec\nrounds: 103694"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-delta]",
            "value": 761666.7289679248,
            "unit": "iter/sec",
            "range": "stddev: 2.1426909954893763e-7",
            "extra": "mean: 1.3129101770731433 usec\nrounds: 113564"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-delta]",
            "value": 675801.7213784055,
            "unit": "iter/sec",
            "range": "stddev: 2.2012831650451318e-7",
            "extra": "mean: 1.4797239609871673 usec\nrounds: 112035"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-delta]",
            "value": 564233.7904226237,
            "unit": "iter/sec",
            "range": "stddev: 2.4231500187578976e-7",
            "extra": "mean: 1.7723149817932342 usec\nrounds: 108012"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-cumulative]",
            "value": 909990.3378076997,
            "unit": "iter/sec",
            "range": "stddev: 1.8657524839347803e-7",
            "extra": "mean: 1.0989127669301926 usec\nrounds: 50349"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-cumulative]",
            "value": 864696.4841296583,
            "unit": "iter/sec",
            "range": "stddev: 2.247629972338205e-7",
            "extra": "mean: 1.1564751544081142 usec\nrounds: 140986"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-cumulative]",
            "value": 767791.9338764257,
            "unit": "iter/sec",
            "range": "stddev: 1.8264639407174004e-7",
            "extra": "mean: 1.3024361886054243 usec\nrounds: 125864"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-cumulative]",
            "value": 675937.2721481097,
            "unit": "iter/sec",
            "range": "stddev: 1.8374092319056255e-7",
            "extra": "mean: 1.47942722084555 usec\nrounds: 132284"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-cumulative]",
            "value": 561015.7915432283,
            "unit": "iter/sec",
            "range": "stddev: 2.624472870948447e-7",
            "extra": "mean: 1.7824810193831169 usec\nrounds: 119041"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[0]",
            "value": 928058.9350179463,
            "unit": "iter/sec",
            "range": "stddev: 1.4963680699679318e-7",
            "extra": "mean: 1.0775177763690864 usec\nrounds: 35315"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[1]",
            "value": 860875.2427354126,
            "unit": "iter/sec",
            "range": "stddev: 1.9432709932376837e-7",
            "extra": "mean: 1.161608500695782 usec\nrounds: 120999"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[3]",
            "value": 769877.7316553034,
            "unit": "iter/sec",
            "range": "stddev: 2.7425042879755667e-7",
            "extra": "mean: 1.298907552306928 usec\nrounds: 133170"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[5]",
            "value": 680333.3660719382,
            "unit": "iter/sec",
            "range": "stddev: 2.0196361987297393e-7",
            "extra": "mean: 1.469867641173813 usec\nrounds: 120335"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[10]",
            "value": 561391.1226588144,
            "unit": "iter/sec",
            "range": "stddev: 2.863626324545245e-7",
            "extra": "mean: 1.781289300165422 usec\nrounds: 122350"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[0]",
            "value": 728686.9304325365,
            "unit": "iter/sec",
            "range": "stddev: 1.1575625633501812e-7",
            "extra": "mean: 1.372331461202984 usec\nrounds: 3857"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[1]",
            "value": 778349.5280853501,
            "unit": "iter/sec",
            "range": "stddev: 1.1327215771464404e-7",
            "extra": "mean: 1.2847698417186486 usec\nrounds: 180370"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[3]",
            "value": 735815.2909390612,
            "unit": "iter/sec",
            "range": "stddev: 2.2502196747247837e-7",
            "extra": "mean: 1.3590367206473535 usec\nrounds: 151402"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[5]",
            "value": 778228.1145528384,
            "unit": "iter/sec",
            "range": "stddev: 1.1175021753937462e-7",
            "extra": "mean: 1.2849702822347782 usec\nrounds: 182672"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[7]",
            "value": 781312.8907440731,
            "unit": "iter/sec",
            "range": "stddev: 1.0890024001496903e-7",
            "extra": "mean: 1.2798969680989944 usec\nrounds: 188211"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[0]",
            "value": 729877.0965991848,
            "unit": "iter/sec",
            "range": "stddev: 2.3166938695863272e-7",
            "extra": "mean: 1.370093683798869 usec\nrounds: 19962"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[1]",
            "value": 790945.8523353825,
            "unit": "iter/sec",
            "range": "stddev: 1.1636028302170423e-7",
            "extra": "mean: 1.2643090510524264 usec\nrounds: 181929"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[3]",
            "value": 786864.3217273889,
            "unit": "iter/sec",
            "range": "stddev: 1.199741832567395e-7",
            "extra": "mean: 1.2708671271366303 usec\nrounds: 186414"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[5]",
            "value": 777795.3310197174,
            "unit": "iter/sec",
            "range": "stddev: 1.217446782977748e-7",
            "extra": "mean: 1.285685269785516 usec\nrounds: 188046"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[7]",
            "value": 729317.2027699009,
            "unit": "iter/sec",
            "range": "stddev: 2.710487062301733e-7",
            "extra": "mean: 1.3711454991080188 usec\nrounds: 196477"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[0]",
            "value": 722190.9340590137,
            "unit": "iter/sec",
            "range": "stddev: 1.7188535862596292e-7",
            "extra": "mean: 1.3846753716217173 usec\nrounds: 26529"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[1]",
            "value": 767302.4072341302,
            "unit": "iter/sec",
            "range": "stddev: 1.254725144943999e-7",
            "extra": "mean: 1.3032671220264604 usec\nrounds: 181652"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[3]",
            "value": 725008.4736724846,
            "unit": "iter/sec",
            "range": "stddev: 2.437888070027492e-7",
            "extra": "mean: 1.3792942238792925 usec\nrounds: 193189"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[5]",
            "value": 776343.1595076551,
            "unit": "iter/sec",
            "range": "stddev: 1.1340362582970958e-7",
            "extra": "mean: 1.288090179907278 usec\nrounds: 180431"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[7]",
            "value": 775437.4655792306,
            "unit": "iter/sec",
            "range": "stddev: 1.150323841377083e-7",
            "extra": "mean: 1.289594640946356 usec\nrounds: 179766"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[0]",
            "value": 715831.4281672441,
            "unit": "iter/sec",
            "range": "stddev: 3.0911872588503337e-7",
            "extra": "mean: 1.3969769426865173 usec\nrounds: 27862"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[1]",
            "value": 762651.6109392435,
            "unit": "iter/sec",
            "range": "stddev: 1.1050467109884719e-7",
            "extra": "mean: 1.3112146957487578 usec\nrounds: 177420"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[3]",
            "value": 759072.521035945,
            "unit": "iter/sec",
            "range": "stddev: 1.1067530787731615e-7",
            "extra": "mean: 1.3173971818071468 usec\nrounds: 177508"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[5]",
            "value": 718963.8911054659,
            "unit": "iter/sec",
            "range": "stddev: 2.555451838633065e-7",
            "extra": "mean: 1.3908904360445946 usec\nrounds: 178482"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[7]",
            "value": 763898.3506928346,
            "unit": "iter/sec",
            "range": "stddev: 1.1721320152722999e-7",
            "extra": "mean: 1.3090746944184755 usec\nrounds: 182300"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[0]",
            "value": 683000.8812740035,
            "unit": "iter/sec",
            "range": "stddev: 2.626610800664765e-7",
            "extra": "mean: 1.4641269541771265 usec\nrounds: 25258"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[1]",
            "value": 691713.6329180668,
            "unit": "iter/sec",
            "range": "stddev: 2.2922958281589828e-7",
            "extra": "mean: 1.4456849661635187 usec\nrounds: 192738"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[3]",
            "value": 689356.2590487639,
            "unit": "iter/sec",
            "range": "stddev: 2.425698180713664e-7",
            "extra": "mean: 1.450628737860291 usec\nrounds: 189842"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[5]",
            "value": 688883.4641622204,
            "unit": "iter/sec",
            "range": "stddev: 2.7708757441670415e-7",
            "extra": "mean: 1.4516243341914752 usec\nrounds: 189741"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[7]",
            "value": 686229.5649471295,
            "unit": "iter/sec",
            "range": "stddev: 2.218585311672065e-7",
            "extra": "mean: 1.4572382932481855 usec\nrounds: 183108"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 66336.6948212661,
            "unit": "iter/sec",
            "range": "stddev: 0.000005107108738863132",
            "extra": "mean: 15.074612967895739 usec\nrounds: 33"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 58066.203042782116,
            "unit": "iter/sec",
            "range": "stddev: 9.43925104796653e-7",
            "extra": "mean: 17.221721889809434 usec\nrounds: 21819"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "107717825+opentelemetrybot@users.noreply.github.com",
            "name": "OpenTelemetry Bot",
            "username": "opentelemetrybot"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "da48e0b131ff34ff382b7d1206f71b2e31929cab",
          "message": "Copy change log updates from release/v1.22.x-0.43bx (#3594)",
          "timestamp": "2023-12-27T09:53:13-08:00",
          "tree_id": "89c2f3018489692d3c4cedf59a50d648af5c849d",
          "url": "https://github.com/open-telemetry/opentelemetry-python/commit/da48e0b131ff34ff382b7d1206f71b2e31929cab"
        },
        "date": 1703699648456,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-delta]",
            "value": 910180.5448925727,
            "unit": "iter/sec",
            "range": "stddev: 1.2609046896928258e-7",
            "extra": "mean: 1.0986831190926285 usec\nrounds: 27129"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-delta]",
            "value": 868618.3803790717,
            "unit": "iter/sec",
            "range": "stddev: 1.333171049830557e-7",
            "extra": "mean: 1.1512535568998576 usec\nrounds: 108066"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-delta]",
            "value": 777678.0064103686,
            "unit": "iter/sec",
            "range": "stddev: 1.2430172241967602e-7",
            "extra": "mean: 1.285879235052348 usec\nrounds: 121108"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-delta]",
            "value": 682604.0664637538,
            "unit": "iter/sec",
            "range": "stddev: 1.3200080181385182e-7",
            "extra": "mean: 1.464978087781579 usec\nrounds: 115234"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-delta]",
            "value": 569424.3184455388,
            "unit": "iter/sec",
            "range": "stddev: 1.3166933671701518e-7",
            "extra": "mean: 1.7561596293075121 usec\nrounds: 120483"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-cumulative]",
            "value": 906660.0203165668,
            "unit": "iter/sec",
            "range": "stddev: 1.108873646700741e-7",
            "extra": "mean: 1.102949261676767 usec\nrounds: 52180"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-cumulative]",
            "value": 872988.0989432184,
            "unit": "iter/sec",
            "range": "stddev: 1.0720760310930397e-7",
            "extra": "mean: 1.1454909880335526 usec\nrounds: 138584"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-cumulative]",
            "value": 777091.4764565593,
            "unit": "iter/sec",
            "range": "stddev: 1.3179537877399286e-7",
            "extra": "mean: 1.2868497857676626 usec\nrounds: 126442"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-cumulative]",
            "value": 681473.7164557874,
            "unit": "iter/sec",
            "range": "stddev: 1.5995312434588472e-7",
            "extra": "mean: 1.4674080244808352 usec\nrounds: 134218"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-cumulative]",
            "value": 571196.0176531699,
            "unit": "iter/sec",
            "range": "stddev: 1.200421223198444e-7",
            "extra": "mean: 1.7507124858969163 usec\nrounds: 112741"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[0]",
            "value": 911849.6083297124,
            "unit": "iter/sec",
            "range": "stddev: 1.0286591932588043e-7",
            "extra": "mean: 1.0966720727464672 usec\nrounds: 34824"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[1]",
            "value": 863222.422414362,
            "unit": "iter/sec",
            "range": "stddev: 1.1720130720971363e-7",
            "extra": "mean: 1.158449982338367 usec\nrounds: 128963"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[3]",
            "value": 779861.9025245387,
            "unit": "iter/sec",
            "range": "stddev: 1.057676706906919e-7",
            "extra": "mean: 1.282278306919262 usec\nrounds: 136922"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[5]",
            "value": 671294.3675241839,
            "unit": "iter/sec",
            "range": "stddev: 1.805404315821395e-7",
            "extra": "mean: 1.4896594525113072 usec\nrounds: 125496"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[10]",
            "value": 569789.5410119913,
            "unit": "iter/sec",
            "range": "stddev: 1.3355460610602352e-7",
            "extra": "mean: 1.755033969602041 usec\nrounds: 127766"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[0]",
            "value": 758041.1250694128,
            "unit": "iter/sec",
            "range": "stddev: 1.2075362244652213e-7",
            "extra": "mean: 1.3191896414702189 usec\nrounds: 3931"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[1]",
            "value": 756881.2899521317,
            "unit": "iter/sec",
            "range": "stddev: 1.5846936826700855e-7",
            "extra": "mean: 1.3212111506458881 usec\nrounds: 186868"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[3]",
            "value": 755980.9122858528,
            "unit": "iter/sec",
            "range": "stddev: 1.7450145092049341e-7",
            "extra": "mean: 1.322784720815647 usec\nrounds: 138120"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[5]",
            "value": 805869.8352837005,
            "unit": "iter/sec",
            "range": "stddev: 6.626374809901985e-8",
            "extra": "mean: 1.2408951870595297 usec\nrounds: 186803"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[7]",
            "value": 755277.3432471977,
            "unit": "iter/sec",
            "range": "stddev: 1.6522316149210835e-7",
            "extra": "mean: 1.324016944160744 usec\nrounds: 195155"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[0]",
            "value": 739915.1779556792,
            "unit": "iter/sec",
            "range": "stddev: 1.1867496935983132e-7",
            "extra": "mean: 1.3515062669249633 usec\nrounds: 19259"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[1]",
            "value": 796259.2281754479,
            "unit": "iter/sec",
            "range": "stddev: 6.664808220887533e-8",
            "extra": "mean: 1.2558724151824332 usec\nrounds: 188707"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[3]",
            "value": 800233.4131603732,
            "unit": "iter/sec",
            "range": "stddev: 7.47034729140134e-8",
            "extra": "mean: 1.2496353983154562 usec\nrounds: 190448"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[5]",
            "value": 800969.4927937024,
            "unit": "iter/sec",
            "range": "stddev: 6.393234035450217e-8",
            "extra": "mean: 1.2484870010617992 usec\nrounds: 190515"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[7]",
            "value": 800059.9956006107,
            "unit": "iter/sec",
            "range": "stddev: 6.759661760903926e-8",
            "extra": "mean: 1.2499062639037375 usec\nrounds: 186868"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[0]",
            "value": 743033.4666760833,
            "unit": "iter/sec",
            "range": "stddev: 1.4918812303732043e-7",
            "extra": "mean: 1.3458344002638822 usec\nrounds: 30845"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[1]",
            "value": 785984.7329425544,
            "unit": "iter/sec",
            "range": "stddev: 7.328958455013075e-8",
            "extra": "mean: 1.2722893436571208 usec\nrounds: 186479"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[3]",
            "value": 788581.1250261521,
            "unit": "iter/sec",
            "range": "stddev: 6.996569717592639e-8",
            "extra": "mean: 1.2681003491769303 usec\nrounds: 183170"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[5]",
            "value": 791440.3763209317,
            "unit": "iter/sec",
            "range": "stddev: 7.040043966982031e-8",
            "extra": "mean: 1.263519059576633 usec\nrounds: 181683"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[7]",
            "value": 781096.0484284323,
            "unit": "iter/sec",
            "range": "stddev: 1.2899090446346727e-7",
            "extra": "mean: 1.280252283969434 usec\nrounds: 180704"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[0]",
            "value": 732751.7398075507,
            "unit": "iter/sec",
            "range": "stddev: 1.5711993359694214e-7",
            "extra": "mean: 1.3647186975804917 usec\nrounds: 25994"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[1]",
            "value": 737853.5342840407,
            "unit": "iter/sec",
            "range": "stddev: 1.7082254931354116e-7",
            "extra": "mean: 1.3552825236113115 usec\nrounds: 198547"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[3]",
            "value": 790460.3189171739,
            "unit": "iter/sec",
            "range": "stddev: 9.833482294055197e-8",
            "extra": "mean: 1.2650856419584322 usec\nrounds: 184049"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[5]",
            "value": 790719.311114318,
            "unit": "iter/sec",
            "range": "stddev: 8.427994599238975e-8",
            "extra": "mean: 1.2646712758168939 usec\nrounds: 186414"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[7]",
            "value": 741837.6885337295,
            "unit": "iter/sec",
            "range": "stddev: 1.5769614845657775e-7",
            "extra": "mean: 1.348003768825143 usec\nrounds: 170058"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[0]",
            "value": 707321.5059070188,
            "unit": "iter/sec",
            "range": "stddev: 1.3504456211485116e-7",
            "extra": "mean: 1.4137842433020202 usec\nrounds: 25005"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[1]",
            "value": 740592.395921075,
            "unit": "iter/sec",
            "range": "stddev: 6.791465888614033e-8",
            "extra": "mean: 1.3502704125881548 usec\nrounds: 166679"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[3]",
            "value": 737413.363031788,
            "unit": "iter/sec",
            "range": "stddev: 6.931582236979234e-8",
            "extra": "mean: 1.3560915086873635 usec\nrounds: 168775"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[5]",
            "value": 738100.4520814412,
            "unit": "iter/sec",
            "range": "stddev: 6.497701887077707e-8",
            "extra": "mean: 1.35482913901489 usec\nrounds: 170328"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[7]",
            "value": 694615.3468159128,
            "unit": "iter/sec",
            "range": "stddev: 1.7495655098908612e-7",
            "extra": "mean: 1.4396457040345532 usec\nrounds: 199432"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 73478.68682863707,
            "unit": "iter/sec",
            "range": "stddev: 0.000004044889680470328",
            "extra": "mean: 13.609388560959786 usec\nrounds: 33"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 57405.99188842752,
            "unit": "iter/sec",
            "range": "stddev: 0.0000011590792618498359",
            "extra": "mean: 17.419784365777854 usec\nrounds: 13913"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "107717825+opentelemetrybot@users.noreply.github.com",
            "name": "OpenTelemetry Bot",
            "username": "opentelemetrybot"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "da48e0b131ff34ff382b7d1206f71b2e31929cab",
          "message": "Copy change log updates from release/v1.22.x-0.43bx (#3594)",
          "timestamp": "2023-12-27T09:53:13-08:00",
          "tree_id": "89c2f3018489692d3c4cedf59a50d648af5c849d",
          "url": "https://github.com/open-telemetry/opentelemetry-python/commit/da48e0b131ff34ff382b7d1206f71b2e31929cab"
        },
        "date": 1703699704150,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-delta]",
            "value": 903362.5240091973,
            "unit": "iter/sec",
            "range": "stddev: 8.190939009461314e-8",
            "extra": "mean: 1.1069752988666364 usec\nrounds: 33295"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-delta]",
            "value": 869968.3698323839,
            "unit": "iter/sec",
            "range": "stddev: 2.2971561751772907e-7",
            "extra": "mean: 1.149467077972811 usec\nrounds: 93565"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-delta]",
            "value": 767149.7260495638,
            "unit": "iter/sec",
            "range": "stddev: 2.3404327694318338e-7",
            "extra": "mean: 1.303526503423912 usec\nrounds: 129617"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-delta]",
            "value": 675035.1522154744,
            "unit": "iter/sec",
            "range": "stddev: 1.9333116284890918e-7",
            "extra": "mean: 1.4814043338602243 usec\nrounds: 120079"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-delta]",
            "value": 565519.516842064,
            "unit": "iter/sec",
            "range": "stddev: 2.1917435344786066e-7",
            "extra": "mean: 1.7682855679042389 usec\nrounds: 126115"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[0-cumulative]",
            "value": 924543.6083642745,
            "unit": "iter/sec",
            "range": "stddev: 1.9610428585314783e-7",
            "extra": "mean: 1.0816147458627992 usec\nrounds: 50444"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[1-cumulative]",
            "value": 872473.4773872736,
            "unit": "iter/sec",
            "range": "stddev: 1.9710543488883831e-7",
            "extra": "mean: 1.1461666468012528 usec\nrounds: 140103"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[3-cumulative]",
            "value": 779011.3374951386,
            "unit": "iter/sec",
            "range": "stddev: 2.090572152784342e-7",
            "extra": "mean: 1.2836783649586365 usec\nrounds: 131942"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[5-cumulative]",
            "value": 682097.0255496381,
            "unit": "iter/sec",
            "range": "stddev: 1.9538695934321316e-7",
            "extra": "mean: 1.4660670880278266 usec\nrounds: 129305"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_counter_add[10-cumulative]",
            "value": 570960.9186225915,
            "unit": "iter/sec",
            "range": "stddev: 2.8383507916167717e-7",
            "extra": "mean: 1.7514333597690699 usec\nrounds: 120160"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[0]",
            "value": 918467.8419087437,
            "unit": "iter/sec",
            "range": "stddev: 2.0278122270342283e-7",
            "extra": "mean: 1.0887697471495763 usec\nrounds: 35217"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[1]",
            "value": 870135.1426680612,
            "unit": "iter/sec",
            "range": "stddev: 2.87128474909558e-7",
            "extra": "mean: 1.149246767500666 usec\nrounds: 143319"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[3]",
            "value": 779954.8688088495,
            "unit": "iter/sec",
            "range": "stddev: 2.626509310047553e-7",
            "extra": "mean: 1.2821254664737263 usec\nrounds: 119651"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[5]",
            "value": 687720.2825897915,
            "unit": "iter/sec",
            "range": "stddev: 2.378569729018133e-7",
            "extra": "mean: 1.4540795514045872 usec\nrounds: 121547"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics.py::test_up_down_counter_add[10]",
            "value": 575945.010259529,
            "unit": "iter/sec",
            "range": "stddev: 2.2415413600986846e-7",
            "extra": "mean: 1.7362768705112765 usec\nrounds: 122072"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[0]",
            "value": 759749.7863186535,
            "unit": "iter/sec",
            "range": "stddev: 1.2263792017597834e-7",
            "extra": "mean: 1.3162228117831691 usec\nrounds: 3905"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[1]",
            "value": 753876.7880224505,
            "unit": "iter/sec",
            "range": "stddev: 3.1602944878971885e-7",
            "extra": "mean: 1.3264767079819146 usec\nrounds: 195939"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[3]",
            "value": 750471.6706577496,
            "unit": "iter/sec",
            "range": "stddev: 3.580979301460419e-7",
            "extra": "mean: 1.332495334732025 usec\nrounds: 134521"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[5]",
            "value": 807936.21388148,
            "unit": "iter/sec",
            "range": "stddev: 1.051555254305144e-7",
            "extra": "mean: 1.2377214720897445 usec\nrounds: 189641"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record[7]",
            "value": 798289.2560949612,
            "unit": "iter/sec",
            "range": "stddev: 1.0644201419338463e-7",
            "extra": "mean: 1.2526787657042502 usec\nrounds: 193607"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[0]",
            "value": 741905.6054359566,
            "unit": "iter/sec",
            "range": "stddev: 4.7514406163009073e-7",
            "extra": "mean: 1.3478803673580315 usec\nrounds: 18982"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[1]",
            "value": 812167.4221761859,
            "unit": "iter/sec",
            "range": "stddev: 1.1376937782064382e-7",
            "extra": "mean: 1.23127322359289 usec\nrounds: 192842"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[3]",
            "value": 811309.227102163,
            "unit": "iter/sec",
            "range": "stddev: 1.0326285465425958e-7",
            "extra": "mean: 1.2325756525311604 usec\nrounds: 188376"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[5]",
            "value": 812145.9677979944,
            "unit": "iter/sec",
            "range": "stddev: 1.1438533817760552e-7",
            "extra": "mean: 1.2313057500135625 usec\nrounds: 193957"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_10[7]",
            "value": 807871.4907165931,
            "unit": "iter/sec",
            "range": "stddev: 1.1215045931227888e-7",
            "extra": "mean: 1.2378206329734278 usec\nrounds: 195582"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[0]",
            "value": 744257.044798504,
            "unit": "iter/sec",
            "range": "stddev: 2.4785908217844893e-7",
            "extra": "mean: 1.343621813174418 usec\nrounds: 29832"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[1]",
            "value": 791850.7206096054,
            "unit": "iter/sec",
            "range": "stddev: 1.1282485254628422e-7",
            "extra": "mean: 1.2628642924390483 usec\nrounds: 185320"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[3]",
            "value": 793953.33668832,
            "unit": "iter/sec",
            "range": "stddev: 9.710175579635002e-8",
            "extra": "mean: 1.2595198657028468 usec\nrounds: 185384"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[5]",
            "value": 741249.2520811807,
            "unit": "iter/sec",
            "range": "stddev: 2.0881732906096672e-7",
            "extra": "mean: 1.3490738738586696 usec\nrounds: 196513"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_49[7]",
            "value": 791989.4990933208,
            "unit": "iter/sec",
            "range": "stddev: 9.804328774578222e-8",
            "extra": "mean: 1.2626430036570084 usec\nrounds: 185448"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[0]",
            "value": 742229.719633831,
            "unit": "iter/sec",
            "range": "stddev: 2.7116543616414014e-7",
            "extra": "mean: 1.3472917798189712 usec\nrounds: 27896"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[1]",
            "value": 788034.6237466835,
            "unit": "iter/sec",
            "range": "stddev: 1.0429645652771527e-7",
            "extra": "mean: 1.2689797755909942 usec\nrounds: 178957"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[3]",
            "value": 788906.908804828,
            "unit": "iter/sec",
            "range": "stddev: 1.1034676745323565e-7",
            "extra": "mean: 1.2675766796300114 usec\nrounds: 180643"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[5]",
            "value": 738496.2078783269,
            "unit": "iter/sec",
            "range": "stddev: 2.3653587960346045e-7",
            "extra": "mean: 1.3541030940063514 usec\nrounds: 199655"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_50[7]",
            "value": 788989.2053879026,
            "unit": "iter/sec",
            "range": "stddev: 1.0453380416466506e-7",
            "extra": "mean: 1.2674444633350275 usec\nrounds: 185833"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[0]",
            "value": 701860.5036169371,
            "unit": "iter/sec",
            "range": "stddev: 1.5091881243372034e-7",
            "extra": "mean: 1.4247845474230905 usec\nrounds: 26293"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[1]",
            "value": 700910.9035367465,
            "unit": "iter/sec",
            "range": "stddev: 2.976140986657648e-7",
            "extra": "mean: 1.4267148577002744 usec\nrounds: 192358"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[3]",
            "value": 727289.6185390982,
            "unit": "iter/sec",
            "range": "stddev: 1.5235954055984968e-7",
            "extra": "mean: 1.3749680656912184 usec\nrounds: 145929"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[5]",
            "value": 693542.0139002737,
            "unit": "iter/sec",
            "range": "stddev: 2.813950972498917e-7",
            "extra": "mean: 1.4418737148688336 usec\nrounds: 170544"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/metrics/test_benchmark_metrics_histogram,.py::test_histogram_record_1000[7]",
            "value": 692089.4125688164,
            "unit": "iter/sec",
            "range": "stddev: 2.2279914484972403e-7",
            "extra": "mean: 1.4449000112403352 usec\nrounds: 193817"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 73424.15079342732,
            "unit": "iter/sec",
            "range": "stddev: 0.000004244337877564226",
            "extra": "mean: 13.619496980134178 usec\nrounds: 34"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 59839.897974511536,
            "unit": "iter/sec",
            "range": "stddev: 9.628069029829527e-7",
            "extra": "mean: 16.711258438741726 usec\nrounds: 25539"
          }
        ]
      }
    ]
  }
}