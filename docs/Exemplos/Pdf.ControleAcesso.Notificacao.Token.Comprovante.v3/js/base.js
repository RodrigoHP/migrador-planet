function DefinirTipoToken(tipoToken){
	let tipoTokenNormalizado = tipoToken != undefined && tipoToken != null ? tipoToken.toLowerCase() : "";
	this.mailChecked = tipoTokenNormalizado == "email";
	this.smsChecked = tipoTokenNormalizado == "sms";
	this.whatsappChecked = tipoTokenNormalizado == "whatsapp";
}

DefinirTipoToken(data.Comprovante.MetodosEnvio.Metodo);

ko.applyBindings(data);