from . import base
from . import parser
from . import util

import os


def perform_builds(target='.', compiler='spcomp', flags='', nosource=False):
    """Main library entrance to build packages."""
    plugins, packages = parser.parse_configs(target)
    output_dir = os.path.join(target, 'builds')
    smbuildfile = os.path.join(target, parser.CONFIG_NAME)
    build(smbuildfile, compiler, plugins, packages, flags=flags, output_dir=output_dir, nosource=nosource)


def build(smbuildfile, compiler, plugins, packages, flags='', output_dir='builds', nosource=False):
    """Performs the entire build process."""
    # setup directory structure, execute user-configurations
    plugin_build_dir = os.path.join(output_dir, 'plugins')
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(plugin_build_dir, exist_ok=True)

    # scan deps for what we need to do
    packages_to_build = set()
    for name, package in packages.items():
        if smbuildfile == package.smbuildfile:
            packages_to_build.add(name)

    plugins_to_compile = set()
    for name in packages_to_build:
        for_this_package = base.find_plugin_deps(packages[name], packages)
        for plugin_name in for_this_package:
            plugins_to_compile.add(plugin_name)

            if plugin_name not in plugins:
                err = 'Package {} uses plugin {}, but it does not exist'.format(name, plugin_name)
                raise ValueError(err)

            # also make sure plugin dependencies are met by the package
            for dep in plugins[plugin_name].deps:
                if dep not in for_this_package:
                    msg = 'Plugin {} depends on {}, but is not part of package {}'
                    msg = msg.format(plugin_name, dep, name)
                    util.warning(msg)

    # also compile any plugins from this smbuildfile
    for plugin_name in plugins:
        if plugins[plugin_name].smbuildfile == smbuildfile:
            plugins_to_compile.add(plugin_name)

    # compile plugins
    compiled_count = 0
    for name in plugins_to_compile:
        plugin = plugins[name]
        if plugin.compile(compiler, plugin_build_dir, flags):
            compiled_count += 1

    # build packages
    for name in packages_to_build:
        package = packages[name]
        print('Building package {}'.format(name))
        package.create(output_dir, packages, plugins, nosource)

    if len(plugins) == 0:
        util.warning('No plugins were found in {}.'.format(smbuildfile))
    elif compiled_count == 0:
        print('All plugins up to date.')
