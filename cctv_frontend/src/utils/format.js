export const formatPrice = (rial) => {
  if (!rial && rial !== 0) return '—'
  return new Intl.NumberFormat('fa-IR').format(rial) + ' ریال'
}

export const formatNumber = (n) =>
  new Intl.NumberFormat('fa-IR').format(n)

export const partTypeLabel = {
  sensor: 'سنسور', lens: 'لنز', board: 'برد', isp: 'ISP',
  housing: 'کیس', ir_cut: 'IR-Cut', motor: 'موتور',
  fpc: 'کابل FPC', power: 'منبع تغذیه', other: 'سایر',
}

export const lensMountLabel = {
  m12: 'M12', cs: 'CS-Mount', c: 'C-Mount', m16: 'M16', none: '—', other: 'سایر',
}

export const statusLabel = {
  pending: 'در انتظار', confirmed: 'تأیید شده',
  awaiting_payment: 'در انتظار پرداخت', paid: 'پرداخت شده',
  cancelled: 'لغو شده', refunded: 'مسترد شده',
}

export const statusColor = {
  pending: 'badge-orange', confirmed: 'badge-blue',
  awaiting_payment: 'badge-orange', paid: 'badge-green',
  cancelled: 'badge-red', refunded: 'badge-red',
}

export const truncate = (str, n = 80) =>
  str && str.length > n ? str.slice(0, n) + '…' : str
