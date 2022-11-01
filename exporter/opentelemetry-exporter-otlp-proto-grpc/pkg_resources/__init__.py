
import toml 

deps  = toml.load('./exporter/opentelemetry-exporter-otlp-proto-grpc/pyproject.toml')['project']
dependencies = deps['dependencies']
backoff = dependencies[0].split(';')[0]
info = backoff.split()
package_name = info[0]
package_version = info[-1]

pkgs = dict([(package_name, package_version)])


def package_version(r):
    def wrapper(f):
        r.version = pkgs[f]        
        return r
    return wrapper

@package_version
def get_distribution(package_name):
    return pkgs[package_name]
  
