import React, { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import { listen } from "@tauri-apps/api/event";
import { Shield, Plus, Key, Settings, Search, Copy, Trash2, Lock } from "lucide-react";
import { cn } from "./lib/utils";

interface SecretInfo {
  name: string;
  created_at?: string;
}

interface VibeSafeStatus {
  initialized: boolean;
  key_exists: boolean;
  passkey_enabled: boolean;
  secrets_count: number;
  claude_integration: boolean;
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost";
  size?: "default" | "sm" | "lg";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none";

    const variants = {
      default: "bg-primary text-primary-foreground hover:bg-primary/90",
      destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      outline: "border border-input hover:bg-accent hover:text-accent-foreground",
      secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
      ghost: "hover:bg-accent hover:text-accent-foreground",
    };

    const sizes = {
      default: "h-10 py-2 px-4",
      sm: "h-9 px-3 rounded-md",
      lg: "h-11 px-8 rounded-md",
    };

    return (
      <button
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    );
  }
);

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

const Card: React.FC<CardProps> = ({ children, className }) => (
  <div className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)}>
    {children}
  </div>
);

const CardHeader: React.FC<CardProps> = ({ children, className }) => (
  <div className={cn("flex flex-col space-y-1.5 p-6", className)}>
    {children}
  </div>
);

const CardTitle: React.FC<CardProps> = ({ children, className }) => (
  <h3 className={cn("text-2xl font-semibold leading-none tracking-tight", className)}>
    {children}
  </h3>
);

const CardContent: React.FC<CardProps> = ({ children, className }) => (
  <div className={cn("p-6 pt-0", className)}>
    {children}
  </div>
);

function App() {
  const [status, setStatus] = useState<VibeSafeStatus | null>(null);
  const [secrets, setSecrets] = useState<SecretInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newSecretName, setNewSecretName] = useState("");
  const [newSecretValue, setNewSecretValue] = useState("");

  useEffect(() => {
    loadData();

    // Listen for system tray events
    const unlisten = listen("show_add_secret", () => {
      setShowAddDialog(true);
    });

    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statusResult, secretsResult] = await Promise.all([
        invoke<VibeSafeStatus>("vibesafe_status"),
        invoke<SecretInfo[]>("vibesafe_list"),
      ]);
      setStatus(statusResult);
      setSecrets(secretsResult);
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSecret = async () => {
    if (!newSecretName.trim() || !newSecretValue.trim()) return;

    try {
      await invoke("vibesafe_add", { name: newSecretName, value: newSecretValue });
      setNewSecretName("");
      setNewSecretValue("");
      setShowAddDialog(false);
      await loadData();
    } catch (error) {
      console.error("Failed to add secret:", error);
    }
  };

  const handleDeleteSecret = async (name: string) => {
    if (!confirm(`Are you sure you want to delete the secret "${name}"?`)) return;

    try {
      await invoke("vibesafe_delete", { name });
      await loadData();
    } catch (error) {
      console.error("Failed to delete secret:", error);
    }
  };

  const handleCopySecret = async (name: string) => {
    try {
      await invoke("copy_secret_to_clipboard", { name });
      // You could show a toast notification here
    } catch (error) {
      console.error("Failed to copy secret:", error);
    }
  };

  const handleInitialize = async () => {
    try {
      await invoke("vibesafe_init");
      await loadData();
    } catch (error) {
      console.error("Failed to initialize VibeSafe:", error);
    }
  };

  const filteredSecrets = secrets.filter((secret) =>
    secret.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Shield className="h-12 w-12 animate-pulse mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading VibeSafe...</p>
        </div>
      </div>
    );
  }

  if (!status?.initialized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <Shield className="h-16 w-16 mx-auto mb-4 text-primary" />
            <CardTitle>Welcome to VibeSafe</CardTitle>
            <p className="text-muted-foreground">
              Secure secrets manager with Touch ID protection
            </p>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-6">
              VibeSafe is not initialized yet. Click the button below to generate your encryption keys and get started.
            </p>
            <Button onClick={handleInitialize} className="w-full">
              <Key className="h-4 w-4 mr-2" />
              Initialize VibeSafe
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="flex h-16 items-center px-6">
          <div className="flex items-center space-x-2">
            <Shield className="h-6 w-6 text-primary" />
            <h1 className="text-lg font-semibold">VibeSafe</h1>
          </div>
          <div className="ml-auto flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              {status.passkey_enabled ? (
                <div className="flex items-center text-green-600">
                  <Lock className="h-4 w-4 mr-1" />
                  <span className="text-sm">Touch ID Protected</span>
                </div>
              ) : (
                <div className="flex items-center text-yellow-600">
                  <Key className="h-4 w-4 mr-1" />
                  <span className="text-sm">File Protected</span>
                </div>
              )}
            </div>
            <Button variant="ghost" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
        <div className="max-w-4xl mx-auto">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center">
                  <Key className="h-8 w-8 text-primary" />
                  <div className="ml-4">
                    <p className="text-2xl font-bold">{status.secrets_count}</p>
                    <p className="text-sm text-muted-foreground">Secrets Stored</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center">
                  <Shield className="h-8 w-8 text-green-600" />
                  <div className="ml-4">
                    <p className="text-2xl font-bold">AES-256</p>
                    <p className="text-sm text-muted-foreground">Encryption</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center">
                  <Lock className="h-8 w-8 text-blue-600" />
                  <div className="ml-4">
                    <p className="text-2xl font-bold">{status.passkey_enabled ? "ON" : "OFF"}</p>
                    <p className="text-sm text-muted-foreground">Touch ID</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Secrets Management */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Your Secrets</CardTitle>
                <Button onClick={() => setShowAddDialog(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Secret
                </Button>
              </div>
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search secrets..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </CardHeader>
            <CardContent>
              {filteredSecrets.length === 0 ? (
                <div className="text-center py-8">
                  <Key className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground">
                    {secrets.length === 0 ? "No secrets stored yet" : "No secrets match your search"}
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredSecrets.map((secret) => (
                    <div
                      key={secret.name}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent"
                    >
                      <div className="flex items-center">
                        <Key className="h-5 w-5 text-muted-foreground mr-3" />
                        <div>
                          <p className="font-medium">{secret.name}</p>
                          {secret.created_at && (
                            <p className="text-sm text-muted-foreground">
                              Created {new Date(secret.created_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopySecret(secret.name)}
                          title="Copy to clipboard"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteSecret(secret.name)}
                          title="Delete secret"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Add Secret Dialog */}
      {showAddDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Add New Secret</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Secret Name</label>
                <input
                  type="text"
                  value={newSecretName}
                  onChange={(e) => setNewSecretName(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="API_KEY, DATABASE_URL, etc."
                />
              </div>
              <div>
                <label className="text-sm font-medium">Secret Value</label>
                <input
                  type="password"
                  value={newSecretValue}
                  onChange={(e) => setNewSecretValue(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Enter your secret value"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-4">
                <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddSecret}>
                  Add Secret
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default App;