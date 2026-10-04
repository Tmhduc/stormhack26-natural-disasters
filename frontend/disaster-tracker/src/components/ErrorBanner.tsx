export default function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="error" role="alert">
      <strong>Data needs attention</strong>
      <p>{message}</p>
      <span>
        Start the backend, extract the boundary files and add your NASA token.
        Then refresh satellite data.
      </span>
    </div>
  );
}
