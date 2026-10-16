import BrandName from '../BrandName';

export default function Footer() {
  return (
    <footer className="border-t border-theme px-6 py-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 text-[13px] sm:flex-row">
        <p className="text-[#555555]">
          <BrandName className="text-accent" /> · Maintenance diagnostics and asset intelligence
        </p>
        <p className="italic text-[#333333]">Decision support. Every suggestion traceable to its source record.</p>
      </div>
    </footer>
  );
}
