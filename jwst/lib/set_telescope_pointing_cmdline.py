"""set_telescope_pointing command line"""

import argparse
import logging
from pathlib import Path

from . import set_telescope_pointing as stp

__all__ = ['stp_cmdline']

# Setup default logging
module_logger = logging.getLogger(__name__)
module_logger.addHandler(logging.NullHandler())
logger_format_debug = logging.Formatter('%(levelname)s:%(filename)s::%(funcName)s: %(message)s')


def stp_cmdline(argv=None, logger=None):
    """Execute set_telescope_pointing from the command-line

    Parameters
    ----------
    argv : dict
        The command-line arguments. If None, `sys.argv` will be used.

    logger : logging.Logger
        Logger to use. If not specified, use the default module logger
    """
    if not logger:
        logger = module_logger

    parser = argparse.ArgumentParser(
        description=('Update basic WCS information in JWST exposures from the engineering database.'
                     ' For detailed information, see'
                     ' https://jwst-pipeline.readthedocs.io/en/latest/jwst/lib/set_telescope_pointing.html')
    )
    parser.add_argument(
        'exposure', type=str, nargs='+',
        help='List of JWST exposures to update.'
    )
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Increase verbosity. Specifying multiple times adds more output.'
    )
    parser.add_argument(
        '--allow-any-file', action='store_true', default=False,
        help='Attempt to update WCS for any file or model. Default: False'
    )
    parser.add_argument(
        '--force-level1bmodel', action='store_true', default=False,
        help='Force unrecognized files to be opened as Level1bModel. Default: False'
    )
    parser.add_argument(
        '--allow-default', action='store_true',
        help='If pointing information cannot be determine, use header information.'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Perform all actions but do not save the results'
    )
    parser.add_argument(
        '--method',
        type=stp.Methods, choices=list(stp.Methods), default=stp.Methods.default,
        help='Algorithmic method to use. Default: %(default)s'
    )
    parser.add_argument(
        '--save-transforms', action='store_true',
        help='Save transforms.'
    )
    parser.add_argument(
        '--override-transforms', type=str, default=None,
        help='Transform matrices to use instead of calculated'
    )
    parser.add_argument(
        '--fgsid', type=int, default=1, choices=stp.FGSIDS,
        help='FGS to use for COARSE mode calculations. Default: %(default)s Choices: %(choices)s'
    )
    parser.add_argument(
        '--tolerance', type=int, default=60,
        help='Seconds beyond the observation time to search for telemetry. Default: %(default)s'
    )
    parser.add_argument(
        '--siaf', type=str, default=None,
        help='SIAF PRD XML folder or file as defined by the `pysiaf` package. Overrides the `prd` option'
    )
    parser.add_argument(
        '--prd', type=str, default=None,
        help='The PRD version to use, as delivered in the `pysiaf` package.'
    )
    parser.add_argument(
        '--engdb_url', type=str, default=None,
        help=('URL of the engineering database.'
              ' If not specified, the environmental variable "ENG_BASE_URL" is used.'
              ' Otherwise, a hardwired default is used.')
    )
    parser.add_argument(
        '--transpose_j2fgs', action='store_false',
        help='Transpose the J2FGS matrix'
    )

    args = parser.parse_args(argv)

    # Set output detail.
    level = stp.LOGLEVELS[min(len(stp.LOGLEVELS) - 1, args.verbose)]
    logger.setLevel(level)
    if level <= logging.DEBUG:
        for handler in logger.handlers:
            handler.setFormatter(logger_format_debug)
    logger.info('set_telescope_pointing called with args %s', args)

    override_transforms = args.override_transforms
    if override_transforms:
        override_transforms = stp.Transforms.from_asdf(override_transforms)

    # Calculate WCS for all inputs.
    exceptions = []
    for filename in args.exposure:
        logger.info(
            '\n------'
            'Setting pointing for {}'.format(filename)
        )

        # Create path for saving the transforms.
        transform_path = None
        if args.save_transforms:
            path = Path(filename)
            transform_path = path.with_name(f'{path.stem}_transforms.asdf')

        try:
            stp.add_wcs(
                filename,
                allow_any_file=args.allow_any_file,
                force_level1bmodel=args.force_level1bmodel,
                siaf_path=args.siaf,
                prd=args.prd,
                engdb_url=args.engdb_url,
                fgsid=args.fgsid,
                tolerance=args.tolerance,
                allow_default=args.allow_default,
                dry_run=args.dry_run,
                method=args.method,
                j2fgs_transpose=args.transpose_j2fgs,
                save_transforms=transform_path,
                override_transforms=override_transforms
            )
        except (TypeError, ValueError) as exception:
            logger.warning('Cannot determine pointing information: %s', str(exception))
            logger.debug('Full exception:', exc_info=exception)
            exceptions.append(exception)

    if exceptions:
        raise RuntimeError('Exceptions occurred while processing.'
                           ' Turn on debugging "-v" for more details.') from exceptions[-1]
