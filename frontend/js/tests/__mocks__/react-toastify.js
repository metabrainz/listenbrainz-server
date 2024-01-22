// Fake react-toastify component because Enzyme doesn't support functional comonents well and throws some errors
const toast = () => {};

toast.loading = () => {};
toast.promise = () => {};
toast.success = () => {};
toast.info = () => {};
toast.error = () => {};
toast.warning = () => {};
toast.warn = () => {};
toast.dark = () => {};
toast.dismiss = () => {};
toast.clearWaitingQueue = () => {};
toast.isActive = () => {};
toast.update = () => {};
toast.done = () => {};
toast.onChange = () => {};
toast.configure = () => {};

exports.toast = toast;
