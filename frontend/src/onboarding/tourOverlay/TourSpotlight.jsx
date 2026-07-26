export default function TourSpotlight({ hole }) {
  if (hole) {
    return (
      <div
        className={`tour-spotlight${hole.round ? ' tour-spotlight--round' : ''}`}
        aria-hidden="true"
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.preventDefault()}
        style={{
          top: hole.top,
          left: hole.left,
          width: hole.width,
          height: hole.height,
        }}
      />
    );
  }

  return <div className="tour-backdrop" aria-hidden="true" />;
}
