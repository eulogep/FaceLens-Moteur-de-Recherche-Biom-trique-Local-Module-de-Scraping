import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>
const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

export const ReticleIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="12" r="6.5" />
    <path d="M12 2v5M12 17v5M2 12h5M17 12h5" />
    <circle cx="12" cy="12" r="1.5" />
  </svg>
)

export const CompareIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M8 4 4 8l4 4M4 8h12M16 20l4-4-4-4M20 16H8" />
  </svg>
)

export const CorpusIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />
  </svg>
)

export const SpiderIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <circle cx="12" cy="13" r="4" />
    <circle cx="12" cy="7" r="2.5" />
    <path d="m8 10-4-2m4 5H3m5 3-4 2m12-8 4-2m-4 5h5m-5 3 4 2" />
  </svg>
)

export const JournalIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M5 3h14v18H5zM8 7h8M8 11h8M8 15h5" />
  </svg>
)

export const UploadIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 20h14" />
  </svg>
)

export const TrashIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14M10 11v6M14 11v6" />
  </svg>
)

export const ExternalIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="M14 4h6v6M20 4l-9 9M18 13v7H4V6h7" />
  </svg>
)

export const CloseIcon = (props: IconProps) => (
  <svg {...base} {...props}>
    <path d="m6 6 12 12M18 6 6 18" />
  </svg>
)
